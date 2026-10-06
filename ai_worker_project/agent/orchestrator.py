"""
Phase 4: Task Orchestrator

Manages the lifecycle of a Run, stores state in SQLite, and wraps the core Agent loop.
Provides the foundation for Phase 5 (API) and Phase 6 (UI).
"""

import json
import asyncio
import logging
import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import defaultdict

from ai_worker_project.agent.models import Run, Step
from ai_worker_project.agent.loop import Agent
from ai_worker_project.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

DB_PATH = Path(os.environ.get("RUNS_DIR", "runs")) / "orchestrator.db"

class Orchestrator:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._init_db()
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        # Per-run event buffers for late-connecting SSE subscribers (fix #7)
        self._event_buffers: Dict[str, List[dict]] = defaultdict(list)
        # Per-run queues for human approval/input (fix #2)
        self._approval_queues: Dict[str, asyncio.Queue] = {}

    def _init_db(self):
        """Initialize SQLite for state persistence."""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    task_description TEXT,
                    status TEXT,
                    final_answer TEXT,
                    data JSON
                )
            ''')

    def save_run(self, run: Run):
        """Persists the run state to SQLite and state.json."""
        run_json = run.model_dump_json(indent=2)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO runs (id, task_description, status, final_answer, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (run.id, run.task_description, run.status, run.final_answer, run.model_dump_json()))
            
        # Also persist to state.json as required by Phase E
        run_dir = DB_PATH.parent / run.id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "state.json").write_text(run_json, encoding="utf-8")

    def get_run(self, run_id: str) -> Optional[Run]:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute('SELECT data FROM runs WHERE id = ?', (run_id,))
            row = cur.fetchone()
            if row:
                return Run.model_validate_json(row[0])
        return None

    def list_runs(self) -> List[Run]:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute('SELECT data FROM runs ORDER BY id DESC LIMIT 50')
            return [Run.model_validate_json(row[0]) for row in cur.fetchall()]

    def resume_active_runs(self):
        """Resumes runs that were interrupted by a server crash (fix Phase E3)."""
        runs = self.list_runs()
        for run in runs:
            if run.status in ("running", "blocked_on_human"):
                logger.info(f"Resuming interrupted run: {run.id}")
                asyncio.create_task(self.execute_run(run))

    async def execute_run(self, run: Run):
        """
        Wraps the core Agent loop, translating loop history/events into structured Steps
        for the database and streaming them live.
        """
        run.status = "running"
        self.save_run(run)

        # Create approval queue for this run (fix #2)
        approval_queue: asyncio.Queue = asyncio.Queue()
        self._approval_queues[run.id] = approval_queue

        agent = Agent(self.registry)

        try:
            async def on_step(step_data: Any):
                if isinstance(step_data, dict) and step_data.get("type") == "budget_update":
                    # Forward budget telemetry to UI (fix #10)
                    self._emit_event(run.id, step_data)
                elif isinstance(step_data, dict) and step_data.get("type") in ("ask_user", "approval_required"):
                    # Human input requested — update run status and emit (fix #1, #2)
                    run.status = "blocked_on_human"
                    self.save_run(run)
                    self._emit_event(run.id, step_data)
                else:
                    # Regular step — append to run.steps incrementally (fix #6)
                    if isinstance(step_data, dict):
                        # Extract Step object if it matches full signature
                        try:
                            if "data" in step_data:
                                step_obj = Step(**{k: v for k, v in step_data["data"].items() if k in Step.model_fields})
                            else:
                                step_obj = Step(**{k: v for k, v in step_data.items() if k in Step.model_fields})
                            run.add_step(step_obj)
                        except Exception:
                            pass
                    
                    if isinstance(step_data, dict) and "type" in step_data:
                        self._emit_event(run.id, step_data)
                    else:
                        self._emit_event(run.id, {"type": "step", "data": step_data})
                # Save incrementally
                self.save_run(run)

            final_answer = await agent.run(
                run.task_description,
                max_steps=getattr(run, 'max_steps', 100) or 100,
                base_contract=None,
                emit_cb=on_step,
                approval_queue=approval_queue,  # pass queue to loop (fix #2)
                run_id=run.id,
                resume_steps=run.steps
            )

            def _derive_status(state: str) -> str:
                if state in ("DONE", "completed"):
                    return "completed"
                elif state in ("FAILED", "failed"):
                    return "failed"
                elif state in ("CANCELLED", "cancelled"):
                    return "cancelled"
                elif state in ("NEEDS_USER", "needs_user"):
                    return "needs_user"
                return "running"

            run.status = _derive_status(agent.state_machine.state)
            run.final_answer = final_answer
            
            self._emit_event(run.id, {
                "type": "run_completed",
                "run_id": run.id,
                "status": run.status,
                "final_answer": run.final_answer
            })

        except Exception as e:
            logger.exception("Run failed critically.")
            run.status = "failed"
            error_msg = str(e)
            
            if "401" in error_msg or "403" in error_msg:
                run.final_answer = "Authentication Error: Please verify your AI Provider API keys in the .env file."
            elif "429" in error_msg or "RateLimit" in error_msg:
                run.final_answer = "Rate Limit Exceeded: The AI Provider is currently overloaded. Please try again in a moment."
            elif "Timeout" in error_msg:
                run.final_answer = "Timeout Error: The AI Provider took too long to respond. Please try again."
            else:
                run.final_answer = f"System Error: {error_msg}"
            self._emit_event(run.id, {
                "type": "run_completed",
                "run_id": run.id,
                "status": "failed",
                "final_answer": run.final_answer
            })

        finally:
            self.save_run(run)
            # Create summary.json
            run_dir = DB_PATH.parent / run.id
            run_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "run_id": run.id,
                "task": run.task_description,
                "status": run.status,
                "final_answer": run.final_answer,
                "total_steps": len(run.steps)
            }
            (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            
            # Clean up approval queue
            self._approval_queues.pop(run.id, None)

        return run

    async def submit_approval(self, run_id: str, approved: bool, user_response: str = "") -> bool:
        """
        Resumes a paused agent with human input. (fix #2)
        Returns True if the approval was delivered to the waiting agent.
        """
        q = self._approval_queues.get(run_id)
        if q is None:
            return False
        await q.put({"approved": approved, "user_response": user_response})
        run = self.get_run(run_id)
        if run:
            run.status = "running"
            self.save_run(run)
            self._emit_event(run_id, {
                "type": "approval_resolved",
                "run_id": run_id,
                "approved": approved,
                "user_response": user_response
            })
            self._emit_event(run_id, {
                "type": "state",
                "state": "EXECUTING"
            })
        return True

    def cancel_run(self, run_id: str) -> bool:
        """Cancels a running run by closing its approval queue (fix #16)."""
        q = self._approval_queues.get(run_id)
        if q:
            q.put_nowait({"approved": False, "user_response": "__CANCEL__"})
        run = self.get_run(run_id)
        if run and run.status in ("running", "blocked_on_human"):
            run.status = "cancelled"
            run.final_answer = "Cancelled by user."
            self.save_run(run)
            self._emit_event(run_id, {
                "type": "run_completed",
                "run_id": run_id,
                "status": "cancelled",
                "final_answer": "Cancelled by user."
            })
            return True
        return False

    def _emit_event(self, run_id: str, event: dict):
        """Emit to all subscribers and append to trace.jsonl."""
        event.setdefault("run_id", run_id)
        
        # Determine sequence number
        if not hasattr(self, '_seqs'):
            self._seqs = {}
        seq = self._seqs.get(run_id, 0) + 1
        self._seqs[run_id] = seq
        event["seq"] = seq
        
        # Append to trace.jsonl
        run_dir = DB_PATH.parent / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        trace_path = run_dir / "trace.jsonl"
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
            
        # Push to live subscribers
        if run_id in self.subscribers:
            for q in list(self.subscribers[run_id]):
                q.put_nowait(event)

    async def subscribe(self, run_id: str, after: int = 0):
        """
        SSE subscription that replays from trace.jsonl first, then streams live.
        """
        # Replay from trace.jsonl
        trace_path = DB_PATH.parent / run_id / "trace.jsonl"
        last_seq_yielded = 0
        run_completed = False
        
        if trace_path.exists():
            with open(trace_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        event = json.loads(line)
                        seq = event.get("seq", 0)
                        if seq > after:
                            yield event
                            last_seq_yielded = seq
                        if event.get("type") == "run_completed":
                            run_completed = True
                    except Exception:
                        pass
                        
        if run_completed:
            return

        # Attach live queue
        if run_id not in self.subscribers:
            self.subscribers[run_id] = []
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers[run_id].append(q)
        try:
            while True:
                event = await q.get()
                seq = event.get("seq", 0)
                if seq > last_seq_yielded:
                    yield event
                    last_seq_yielded = seq
                if event.get("type") == "run_completed":
                    break
        finally:
            if run_id in self.subscribers:
                try:
                    self.subscribers[run_id].remove(q)
                except ValueError:
                    pass
                if not self.subscribers[run_id]:
                    del self.subscribers[run_id]
