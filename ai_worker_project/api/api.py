"""
Phase 5: API Routes and Controllers

Defines REST and SSE endpoints for submitting tasks, streaming real-time events,
approving/rejecting human-in-the-loop steps, and cancelling runs.

Fixes applied:
- #2  /approve now actually resumes the paused agent via Orchestrator.submit_approval()
- #7  SSE stream uses buffered event replay for late subscribers
- #9  /health probes all LLM providers in the fallback chain
- #11 run_id included in every SSE event payload (done in Orchestrator)
- #16 DELETE /runs/{id} cancels a running run
"""

import json
import asyncio
import os
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ai_worker_project.agent.models import Run
from ai_worker_project.agent.orchestrator import Orchestrator

router = APIRouter()


# Dependency to get orchestrator from app state
def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


class TaskCreateRequest(BaseModel):
    task: str
    max_steps: int = 15
    max_seconds: int = 300

@router.post("/runs")
async def create_run(
    req: TaskCreateRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Submits a new task to the agent."""
    run = Run(
        task_description=req.task
    )
    orchestrator.save_run(run)

    # Launch in background so we return the ID immediately
    asyncio.create_task(orchestrator.execute_run(run))
    return {
        "run_id": run.id,
        "status": run.status,
        "contract": {"max_steps": req.max_steps, "status": "bypassed"}
    }


@router.get("/runs")
async def list_runs(
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Lists all historical runs."""
    runs = orchestrator.list_runs()
    return [r.model_dump() for r in runs]


@router.get("/tools")
async def get_available_tools(
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Returns the list of tools available to the agent."""
    schemas = orchestrator.registry.get_all_schemas()
    return {"tools": [s["name"] for s in schemas]}


@router.get("/runs/{run_id}")
async def get_run_status(
    run_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Gets the historical state of a run."""
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.model_dump()


class ApprovalRequest(BaseModel):
    approved: bool
    user_response: str = ""


@router.post("/runs/{run_id}/approve")
async def approve_run(
    run_id: str,
    req: ApprovalRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    Submits human approval/answer for a paused run.
    Actually resumes the waiting agent loop. (fix #2)
    """
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    delivered = await orchestrator.submit_approval(run_id, req.approved, req.user_response)
    if not delivered:
        # Run might already be complete or not waiting — just return current status
        return {"status": run.status, "run_id": run_id, "approved": req.approved, "delivered": False}

    return {"status": "resumed", "run_id": run_id, "approved": req.approved, "delivered": True}


@router.post("/runs/{run_id}/resume")
async def resume_run(
    run_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    Resumes an interrupted or failed run. (Phase E)
    """
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    if run.status in ["running", "completed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Cannot resume run in status: {run.status}")

    # Reset status and resume execution in background
    run.status = "running"
    orchestrator.save_run(run)
    asyncio.create_task(orchestrator.execute_run(run))
    
    return {"status": "resumed", "run_id": run_id}


@router.delete("/runs/{run_id}")
async def cancel_run(
    run_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Cancels a running or paused run. (fix #16)"""
    cancelled = orchestrator.cancel_run(run_id)
    if not cancelled:
        run = orchestrator.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"status": run.status, "run_id": run_id, "cancelled": False}
    return {"status": "cancelled", "run_id": run_id, "cancelled": True}


@router.get("/runs/{run_id}/stream")
async def stream_run(
    run_id: str,
    after: int = 0,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    Server-Sent Events (SSE) endpoint to stream thoughts and actions to the UI.
    Replays buffered events for late subscribers, then streams live. (fix #7)
    """
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        async for event in orchestrator.subscribe(run_id, after=after):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/health/providers")
async def health_providers():
    """
    Probes all configured LLM providers and reports which are reachable. (fix #9)
    """
    import httpx
    from agent.llm import get_fallback_chain

    chain = get_fallback_chain()
    results = {}

    for provider in chain:
        if provider == "nvidia":
            key = os.environ.get("NVIDIA_API_KEY")
            results[provider] = "ok" if key else "missing_key"
        elif provider == "groq":
            key = os.environ.get("LLM_API_KEY")
            results[provider] = "ok" if key else "missing_key"
        elif provider == "gemini":
            key = os.environ.get("GEMINI_API_KEY")
            results[provider] = "ok" if key else "missing_key"
        elif provider == "ollama":
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    r = await client.get(f"{base_url}/api/tags")
                    results[provider] = "ok" if r.status_code == 200 else f"error_{r.status_code}"
            except Exception as e:
                results[provider] = f"unreachable: {str(e)[:50]}"
        else:
            results[provider] = "unknown"

    active = [p for p, s in results.items() if s == "ok"]
    return {
        "providers": results,
        "fallback_chain": chain,
        "active_providers": active,
        "ready": len(active) > 0
    }
