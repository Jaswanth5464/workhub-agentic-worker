import json
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional

from ai_worker_project.agent.llm import generate_response, extract_json, prune_history_for_context
from ai_worker_project.tools import ToolRegistry
from ai_worker_project.tools.base import RiskLevel
from ai_worker_project.tools.memory import get_all_memories
from ai_worker_project.agent.state import StateMachine, AgentState
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.loader import settings

logger = logging.getLogger(__name__)

DATABASE_SCHEMA_DOC = """COMPANY DATABASE SCHEMA (SQLite):
1. `employees`:
   - Columns: id (TEXT), name (TEXT), department (TEXT), role (TEXT), status (TEXT: 'active', 'inactive', 'terminated'), email (TEXT), joined (TEXT), emergencyContact (TEXT), phone (TEXT), manager (TEXT)
   - IMPORTANT: There is NO 'salary' column in employees.
2. `expenses`:
   - Columns: id (TEXT), employee (TEXT: stores employee full NAME, e.g. 'John Doe', 'Bob Wilson'), date (TEXT), amount (TEXT), category (TEXT), description (TEXT), status (TEXT: 'pending', 'approved', 'rejected', 'cancelled'), receiptId (TEXT)
3. `tasks`:
   - Columns: id (TEXT), title (TEXT), assignedTo (TEXT: stores employee full NAME, e.g. 'Admin', 'Alice Smith'), dueDate (TEXT), priority (TEXT: 'low', 'medium', 'high'), status (TEXT: 'pending', 'in-progress', 'completed')
4. `leaves`:
   - Columns: id (TEXT), employee (TEXT: stores employee full NAME, e.g. 'Jane Smith', 'Bob Wilson'), type (TEXT), dates (TEXT), status (TEXT: 'pending', 'approved', 'rejected', 'cancelled')
5. `documents`:
   - Columns: id (TEXT), type (TEXT), name (TEXT), relatedTo (TEXT), content (TEXT)
6. `emails`:
   - Columns: id (TEXT), from_email (TEXT), subject (TEXT), date (TEXT), read (INTEGER), body (TEXT)
7. `benefits`:
   - Columns: id (TEXT), name (TEXT), provider (TEXT), coverage (TEXT), enrolled (INTEGER), status (TEXT)
8. `audit_logs`:
   - Columns: id (INTEGER), table_name (TEXT), record_id (TEXT), action (TEXT), details (TEXT), timestamp (TEXT)

IMPORTANT QUERYING RULE:
- In `tasks`, `leaves`, and `expenses`, the employee field stores employee full NAME (e.g. 'Olivia Hall', 'John Doe'), NOT employee IDs ('EMP-001'). Always match by employee `name` (e.g. `WHERE employee IN ('Olivia Hall', 'Sam White')` or `JOIN employees ON leaves.employee = employees.name`).
"""

SYSTEM_PROMPT = """You are an Autonomous AI Task Worker.
Your goal is to complete the given task step-by-step using available tools.

{database_schema}

{memory_section}

CRITICAL INSTRUCTION - SECURITY & SAFETY GUARDRAILS:
1. STRICTLY FORBIDDEN: NEVER attempt table restructuring, column changes, or DDL operations (ALTER TABLE, DROP TABLE, RENAME TABLE/COLUMN, ADD COLUMN, DROP COLUMN). Restructuring the database schema is prohibited and will be auto-rejected by security guardrails.
2. PERMITTED DATA OPERATIONS: Only data operations (INSERT/CREATE, UPDATE, DELETE) are permitted.
3. HUMAN AUTHORIZATION: Any state mutation (e.g. cancelling pending leave requests, cancelling pending expense claims, reassigning tasks, updating employee records, or SQL UPDATE/DELETE) requires explicit human approval before execution.

CRITICAL INSTRUCTION - SCHEMA ACCURACY:
- Only write SQL queries using the EXACT tables and column names listed in the COMPANY DATABASE SCHEMA above.
- NEVER assume or invent columns that do not exist in the schema.

CRITICAL INSTRUCTION - STEP-BY-STEP EXECUTION:
1. You MUST NEVER fabricate or assume database records exist.
2. You MUST ACTUALLY execute the appropriate tools step-by-step (e.g. `get_all_employees`, `get_all_leaves`, `get_employee`, `get_all_expenses`, `create_employee`, `sql_query`, `update_leave`, `manage_leave`, `update_expense`, `update_task`).
3. NEVER call the "finish" tool on your first step if the user requested actions or queries that require database access. First execute the queries and actions, inspect the real observations, and only call "finish" once you have gathered real data and completed all subgoals!

CRITICAL INSTRUCTION - TOKEN EFFICIENCY & TARGETED LOOKUPS:
1. When looking up a person or entity (e.g. 'Jaswanth' or 'Vikram Patel'), NEVER call `get_all_employees()` without filters.
2. ALWAYS use targeted lookups:
   - `get_employee(name="Vikram Patel")` or `get_employee(name="Jaswanth")`
   - `get_all_employees(department="Engineering", limit=20)`
   - `get_all_expenses(status="pending", limit=20)`
   - `sql_query(query="SELECT id, name, email, department FROM employees WHERE name LIKE '%Vikram%' LIMIT 5")`
3. Always specify exact filters or use WHERE clauses with LIMIT clauses.

CRITICAL INSTRUCTION - VERIFICATION PHASE:
Before calling the "finish" tool, you MUST verify that your action was successful.
For example, if you CREATED or UPDATED a database record (e.g. cancelled leaves/expenses or reassigned tasks), you MUST run a targeted SELECT query or getter tool afterwards to confirm the updated status actually exists in the database.
Only call "finish" once you have explicitly observed proof of success.

You MUST respond in valid JSON with this exact format:
{
    "thought": "<reasoning for next action>",
    "action": {
        "tool": "tool_name",
        "args": {
            "arg1": "value1"
        }
    }
}

When finished and verified, use the "finish" tool:
{
    "thought": "Summary of completed work",
    "action": {
        "tool": "finish",
        "args": {
            "answer": "Final response to user"
        }
    }
}

CRITICAL INSTRUCTION - TOOL CALLING & SECURITY GUARDS:
1. When performing database operations or actions (e.g. creating/updating employees, tasks, expenses, leaves, documents, or running SQL queries), ALWAYS call the real tool directly (e.g. `create_employee`, `sql_query`, `update_expense`, `create_task`, `update_leave`).
2. NEVER invent or call fake tools like 'approval_required'. Our automated security guard automatically intercepts write and mutation operations and prompts the human operator for authorization on your behalf.
3. If you need to ask the human operator a clarifying question or request specific user input, use the 'ask_user' tool with {"question": "..."}.
4. COMPANY MEMORY: If you ask the human a question and they provide an answer or a rule, you MUST use the 'memorize_fact' tool to save that rule so you never have to ask it again in future runs!

Available Tools:
{tool_descriptions}
"""


class RunState:
    def __init__(self, goal: str):
        self.goal = goal
        self.step = 0
        self.usage = {}
        self.action_history: List[str] = []

class Agent:
    """
    A cleaner ReAct-style Agent loop inspired by the ai-workforce-main architecture.
    Replaces the complex state-machine / contract loop with a simple, robust cycle.
    """
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.history: List[Dict[str, str]] = []
        self.state_machine = StateMachine()

    def _build_system_prompt(self) -> str:
        tools_info = []
        for schema in self.registry.get_all_schemas():
            info = f"- {schema['name']}: {schema.get('description', 'No description')} \n  Parameters: {schema.get('parameters', {})}"
            tools_info.append(info)
            
        memories = get_all_memories()
        memory_section = ""
        if memories:
            memory_section = "COMPANY MEMORY & RULES (Extremely Important):\n"
            for m in memories:
                memory_section += f"- [{m['topic']}]: {m['fact']}\n"
            memory_section += "\n"
            
        return (
            SYSTEM_PROMPT
            .replace("{database_schema}", DATABASE_SCHEMA_DOC)
            .replace("{tool_descriptions}", "\n".join(tools_info))
            .replace("{memory_section}", memory_section)
        )

    async def run(
        self,
        task: str,
        max_steps: int = settings.agent.max_steps,
        base_contract: Any = None,
        emit_cb=None,
        approval_queue: Optional[asyncio.Queue] = None,
        run_id: str = "",
        resume_steps: Optional[list] = None
    ) -> str:
        async def _emit(payload: dict):
            if emit_cb:
                payload["run_id"] = run_id
                payload["seq"] = getattr(_emit, "seq", 1)
                _emit.seq = payload["seq"] + 1
                await emit_cb(payload)
                
        self.state_machine.set_emitter(_emit)

        self.history = [{"role": "user", "content": f"Task: {task}"}]
        
        # Load resume steps if provided
        if resume_steps:
            for step in resume_steps:
                action = {"tool": step.tool_name, "args": step.tool_args}
                parsed = {"thought": step.thought, "action": action}
                self.history.append({"role": "assistant", "content": json.dumps(parsed)})
                self.history.append({"role": "user", "content": step.observation})

        system_prompt = self._build_system_prompt()
        state = RunState(goal=task)
        final_answer = None
        
        await self.state_machine.transition(AgentState.UNDERSTANDING)
        
        # Dynamic LLM Planning Engine (Proportional to task complexity)
        planning_prompt = (
            f"{DATABASE_SCHEMA_DOC}\n\n"
            f"Analyze the following user task and decompose it into the exact minimal sequential subgoals strictly aligned with the database schema above:\n"
            f"Task: \"{task}\"\n\n"
            f"Output ONLY valid JSON in this exact structure:\n"
            f'{{\n'
            f'  "intent": "Short goal summary",\n'
            f'  "subgoals": [\n'
            f'    {{"id": "G1", "title": "Brief title", "desc": "Detailed objective", "status": "in_progress"}}\n'
            f'  ],\n'
            f'  "success_points": [\n'
            f'    {{"id": "SP1", "label": "Target operation validated", "status": "pending"}}\n'
            f'  ]\n'
            f'}}\n'
        )

        try:
            plan_raw = await generate_response(
                system_prompt="You are a strict JSON planning engine. Output ONLY valid JSON.",
                messages=[{"role": "user", "content": planning_prompt}],
                require_json=True
            )
            parsed_plan = extract_json(plan_raw)
            active_subgoals = parsed_plan.get("subgoals", [])
            success_points = parsed_plan.get("success_points", [])
            if not isinstance(active_subgoals, list) or len(active_subgoals) == 0:
                raise ValueError("Invalid subgoals structure")
        except Exception as e:
            logger.warning(f"Dynamic LLM planning failed fallback: {e}")
            active_subgoals = [
                {"id": "G1", "title": "Analyze Task Requirements", "desc": task[:60], "status": "in_progress"},
                {"id": "G2", "title": "Execute Operations & Tool Queries", "desc": "Perform operations in strict read-only / guard mode", "status": "pending"},
                {"id": "G3", "title": "Verify Integrity & Compile Final Report", "desc": "Audit results and present verified outcome", "status": "pending"}
            ]
            success_points = [
                {"id": "SP1", "label": "Target schema & records validated", "status": "pending"},
                {"id": "SP2", "label": "Security policies & authorization respected", "status": "pending"},
                {"id": "SP3", "label": "Verification check passed", "status": "pending"}
            ]

        # Emit rich Execution Contract, Subgoals & Success Points
        await _emit({
            "type": "contract",
            "contract": {
                "target_goal": task,
                "safety_mode": "STRICT_HUMAN_IN_THE_LOOP",
                "max_steps": max_steps,
                "read_only_default": True,
                "budget_seconds": 300,
                "subgoals": active_subgoals,
                "success_points": success_points
            }
        })

        while final_answer is None:
            state.step += 1
            if state.step > max_steps:
                final_answer = "Error: Maximum steps reached without completion."
                break

            pruned_history = prune_history_for_context(self.history)
            
            try:
                response_text = await generate_response(
                    system_prompt=system_prompt,
                    messages=pruned_history,
                    require_json=False
                )
            except Exception as e:
                # Provide a clean, generic user-facing message while preserving the technical detail
                error_msg = str(e)
                if "401" in error_msg or "403" in error_msg:
                    final_answer = "Authentication Error: Please verify your AI Provider API keys in the .env file."
                elif "429" in error_msg or "RateLimit" in error_msg:
                    final_answer = "Rate Limit Exceeded: The AI Provider is currently overloaded. Please try again in a moment."
                elif "Timeout" in error_msg:
                    final_answer = "Timeout Error: The AI Provider took too long to respond. Please try again."
                else:
                    final_answer = f"AI Provider Error: Unable to complete the request. Details: {error_msg}"
                break
                
            self.history.append({"role": "assistant", "content": response_text})
            
            try:
                parsed = extract_json(response_text)
            except Exception as e:
                self.history.append({"role": "user", "content": f"Error: Invalid JSON. {e}. Please respond with ONLY valid JSON."})
                continue
                
            thought = parsed.get("thought", parsed.get("reason", ""))
            action = parsed.get("action", {})
            tool_name = action.get("tool")
            tool_args = action.get("args", {})
            
            # Graceful alias fallback for LLM hallucinated tool names
            if tool_name in ["approval_required", "ask_approval", "request_approval"]:
                q = tool_args.get("request") or tool_args.get("question") or tool_args.get("message") or "Do you approve this operation?"
                tool_name = "ask_user"
                tool_args = {"question": f"Human approval requested: {q}"}
            
            if thought:
                await _emit({"type": "thought", "data": {"thought": thought}})
            
            # Dynamic Phase Advancement
            if state.step > 1 and self.state_machine.state == AgentState.UNDERSTANDING:
                await self.state_machine.transition(AgentState.PLANNING)
                await self.state_machine.transition(AgentState.EXECUTING)
                
            if tool_name == "db_select" or "verify" in thought.lower() or "confirm" in thought.lower():
                if self.state_machine.state != AgentState.VERIFYING:
                    await self.state_machine.transition(AgentState.VERIFYING)
            
            # Loop Breaker Check
            action_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
            state.action_history.append(action_signature)
            
            if len(state.action_history) >= 3 and len(set(state.action_history[-3:])) == 1:
                obs = f"SYSTEM ERROR: Loop detected! You just tried '{tool_name}' with these exact arguments 3 times in a row without making progress. You MUST try a different approach, a different selector, or scroll to find new elements."
                self.history.append({"role": "user", "content": f"Observation:\n{obs}"})
                await _emit({"type": "observation", "data": {"observation": obs}})
                continue
            
            # Guard & Policy Checks
            is_schema_alteration = False
            is_mutation = False
            blocked_reason = ""
            
            tool_obj = self.registry.get_tool(tool_name) if tool_name else None
            
            # 1. Detect DDL / Schema Alteration / Table Restructuring
            if tool_name == "sql_query":
                q = str(tool_args.get("query", "")).strip().upper()
                ddl_patterns = [
                    r"\bALTER\s+TABLE\b",
                    r"\bDROP\s+TABLE\b",
                    r"\bDROP\s+COLUMN\b",
                    r"\bADD\s+COLUMN\b",
                    r"\bRENAME\s+TO\b",
                    r"\bRENAME\s+COLUMN\b",
                    r"\bALTER\b",
                    r"\bDROP\b",
                    r"\bTRUNCATE\b",
                ]
                if any(re.search(p, q) for p in ddl_patterns):
                    is_schema_alteration = True
            elif tool_name and any(tool_name.startswith(kw) for kw in ["alter", "drop"]):
                is_schema_alteration = True

            # Hard Forbidden Guardrail: Auto-reject schema restructuring / column changes immediately
            if is_schema_alteration:
                blocked_reason = (
                    "FORBIDDEN: Table restructuring and column alterations (ALTER, DROP, RENAME, ADD/DROP COLUMN) "
                    "are strictly prohibited by system security policy. No user or agent is permitted to restructure the database schema."
                )
                await _emit({
                    "type": "guard",
                    "tool": tool_name,
                    "checks": [
                        {"rule": "Schema & Table Restructuring Policy", "passed": False, "reason": blocked_reason}
                    ],
                    "verdict": "rejected"
                })
                obs = (
                    "Security Policy Violation: Auto-rejected. Table restructuring and column alterations "
                    "(ALTER, DROP, RENAME, ADD/DROP COLUMN) are strictly forbidden because restructuring the "
                    "database schema is not allowed. Only data-level operations (INSERT, UPDATE, DELETE) "
                    "are permitted with human authorization."
                )
                self.history.append({"role": "user", "content": f"Observation from {tool_name}:\n{obs}"})
                await _emit({"type": "observation", "data": {"observation": obs}})
                await _emit({"type": "assess", "status": "failed", "expected": "Policy Compliance", "actual": "Auto-rejected schema alteration"})
                await self.state_machine.transition(AgentState.RECOVERING)
                continue

            # 2. Detect Data Mutations (UPDATE, INSERT, DELETE, status changes, task reassignments, cancellations)
            if tool_name == "sql_query":
                q = str(tool_args.get("query", "")).strip().upper()
                if re.search(r"\b(UPDATE|INSERT|DELETE|REPLACE)\b", q):
                    is_mutation = True
            elif tool_obj:
                if getattr(tool_obj, "effect", "") == "write":
                    is_mutation = True
                elif getattr(tool_obj, "risk_level", None) in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
                    is_mutation = True
                elif hasattr(tool_obj, "requires_approval") and tool_obj.requires_approval(tool_args):
                    is_mutation = True
                elif tool_name and any(tool_name.startswith(kw) for kw in [
                    "create", "update", "delete", "post", "cancel", "reassign", 
                    "manage", "onboard", "offboard", "issue", "approve", "modify", "patch", "remove", "add", "set"
                ]):
                    is_mutation = True
            elif tool_name and any(tool_name.startswith(kw) for kw in [
                "create", "update", "delete", "post", "cancel", "reassign", 
                "manage", "onboard", "offboard", "issue", "approve", "modify", "patch", "remove", "add", "set"
            ]):
                is_mutation = True

            if is_mutation:
                blocked_reason = "Safety Policy: Database mutations, cancellations, and state modifications require explicit human authorization."

            await _emit({
                "type": "guard",
                "tool": tool_name,
                "checks": [
                    {"rule": "Read-only enforcement & Write policy", "passed": not is_mutation, "reason": blocked_reason or "Safe read operation"}
                ],
                "verdict": "allowed" if not is_mutation else "requires_approval"
            })
            
            # Dynamic Subgoal and Success Points Progression
            if active_subgoals:
                num_goals = len(active_subgoals)
                active_idx = min(num_goals - 1, state.step - 1)
                for i in range(num_goals):
                    if i < active_idx:
                        active_subgoals[i]["status"] = "completed"
                    elif i == active_idx:
                        active_subgoals[i]["status"] = "in_progress"
                    else:
                        active_subgoals[i]["status"] = "pending"
                
                if len(success_points) >= 1 and state.step >= 1:
                    success_points[0]["status"] = "passed"
                if len(success_points) >= 2 and (state.step >= 2 or not is_mutation):
                    success_points[1]["status"] = "passed"
                if len(success_points) >= 3 and ("verify" in thought.lower() or state.step >= 3):
                    success_points[2]["status"] = "passed"
                    
                await _emit({
                    "type": "plan_update",
                    "subgoals": active_subgoals,
                    "success_points": success_points
                })

            # Emit explicit action event with active subgoal metadata
            active_sg = active_subgoals[active_idx] if active_subgoals and 'active_idx' in locals() else {}
            await _emit({
                "type": "action",
                "tool": tool_name,
                "args": tool_args,
                "subgoal_id": active_sg.get("id", "G1"),
                "subgoal_title": active_sg.get("title", "Execute Step"),
                "step": state.step
            })

            if tool_name == "finish":
                await self.state_machine.transition(AgentState.DONE)
                final_answer = tool_args.get("answer", tool_args.get("final_answer", "Task complete."))
                if not isinstance(final_answer, str):
                    final_answer = json.dumps(final_answer, indent=2)
                for sg in active_subgoals:
                    sg["status"] = "completed"
                for sp in success_points:
                    sp["status"] = "passed"
                await _emit({
                    "type": "plan_update",
                    "subgoals": active_subgoals,
                    "success_points": success_points
                })
                break
                
            # Execute tool
            if not tool_name:
                obs = "Error: No tool specified."
            elif tool_name == "ask_user":
                await self.state_machine.transition(AgentState.NEEDS_USER)
                await _emit({
                    "type": "ask_user",
                    "question": tool_args.get("question", "Please provide more information."),
                    "step": state.step
                })
                if approval_queue:
                    human_resp = await approval_queue.get()
                    if human_resp.get("user_response") == "__CANCEL__":
                        final_answer = "Cancelled by user."
                        break
                    obs = f"Human answered: {human_resp.get('user_response', 'No answer.')}"
                else:
                    obs = "No human available."
                await self.state_machine.transition(AgentState.EXECUTING)
            else:
                try:
                    tool = self.registry.get_tool(tool_name)
                    if not tool:
                        obs = f"Error: Tool {tool_name} not found."
                    else:
                        _was_approved = False
                        if is_mutation or (hasattr(tool, "requires_approval") and tool.requires_approval(tool_args)):
                            await self.state_machine.transition(AgentState.WAITING_APPROVAL)
                            preview_data = tool.preview(tool_args) if hasattr(tool, "preview") else {}
                            if not preview_data and tool_name == "sql_query":
                                preview_data = {"sql": tool_args.get("query", "")}
                            elif not preview_data:
                                preview_data = tool_args
                                
                            await _emit({
                                "type": "approval_required",
                                "data": {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "preview": preview_data,
                                    "risk": "CRITICAL" if any(k in str(tool_args).upper() for k in ["DROP", "ALTER", "DELETE"]) else "HIGH",
                                    "reason": blocked_reason or "This operation mutates database records or cancels items and requires authorization."
                                }
                            })
                            if approval_queue:
                                human_resp = await approval_queue.get()
                                if human_resp.get("user_response") == "__CANCEL__":
                                    final_answer = "Cancelled by user."
                                    break
                                if not human_resp.get("approved"):
                                    obs = f"User denied this action. Reason: {human_resp.get('user_response', 'Rejected by administrator.')}"
                                    self.history.append({"role": "user", "content": f"Observation:\n{obs}"})
                                    await self.state_machine.transition(AgentState.EXECUTING)
                                    await _emit({"type": "observation", "data": {"observation": obs}})
                                    continue
                                _was_approved = True
                            else:
                                obs = "Safety violation: Action requires human approval, but no approval handler was provided."
                                self.history.append({"role": "user", "content": f"Observation:\n{obs}"})
                                await self.state_machine.transition(AgentState.RECOVERING)
                                await _emit({"type": "observation", "data": {"observation": obs}})
                                continue
                                
                            await self.state_machine.transition(AgentState.EXECUTING)
                            
                        # Run the tool
                        result = await self.registry.execute(tool_name, kwargs={**tool_args, "run_id": run_id}, approval_granted=_was_approved)
                        is_ok = getattr(result, "ok", getattr(result, "success", False))
                        if is_ok:
                            data = getattr(result, "data", "Success")
                            if isinstance(data, (dict, list)):
                                obs = json.dumps(data, indent=2)
                            else:
                                obs = str(data)
                            await _emit({"type": "assess", "status": "success", "expected": "Success", "actual": "Command executed successfully"})
                        else:
                            obs = f"Failed: {getattr(result, 'detail', getattr(result, 'error', 'Unknown error'))}"
                            await _emit({"type": "assess", "status": "failed", "expected": "Success", "actual": obs})
                            await self.state_machine.transition(AgentState.RECOVERING)

                        # Synchronize trace directly into active subgoal
                        if active_subgoals and 'active_idx' in locals() and active_idx < len(active_subgoals):
                            sg = active_subgoals[active_idx]
                            sg["thought"] = thought
                            sg["guard"] = {"passed": not is_mutation or _was_approved, "rule": blocked_reason or "Safe read/approved write"}
                            sg["action"] = {"tool": tool_name, "args": tool_args}
                            sg["observation"] = obs
                            sg["status"] = "completed" if is_ok else "in_progress"
                            sg["verified"] = is_ok
                            await _emit({
                                "type": "plan_update",
                                "subgoals": active_subgoals,
                                "success_points": success_points
                            })
                except Exception as e:
                    obs = f"Error executing {tool_name}: {e}"
                    await _emit({"type": "assess", "status": "failed", "expected": "Success", "actual": obs})
                    await self.state_machine.transition(AgentState.RECOVERING)
                    
            self.history.append({"role": "user", "content": f"Observation from {tool_name}:\n{obs}"})
            await _emit({"type": "observation", "data": {"observation": obs}})
            
        # Determine final state based on final answer
        if "Error:" in final_answer:
            await self.state_machine.transition(AgentState.FAILED)
        elif "Cancelled" in final_answer:
            await self.state_machine.transition(AgentState.CANCELLED)
        else:
            await self.state_machine.transition(AgentState.DONE)
            
        return final_answer
