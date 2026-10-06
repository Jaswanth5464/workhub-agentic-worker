import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai_worker_project.tools import get_default_registry
from ai_worker_project.agent.orchestrator import Orchestrator

app = FastAPI(
    title="AI Task Worker Agent API",
    description="Autonomous AI Task Worker \u2014 contract-driven agent",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_registry = get_default_registry()
_orchestrator = Orchestrator(_registry)
app.state.orchestrator = _orchestrator

from ai_worker_project.api.api import router as api_router
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def on_startup():
    _orchestrator.resume_active_runs()

@app.get("/api/health")
async def health():
    from ai_worker_project.agent.llm import get_fallback_chain
    chain = get_fallback_chain()
    return {
        "status": "ok",
        "fallback_chain": chain
    }
