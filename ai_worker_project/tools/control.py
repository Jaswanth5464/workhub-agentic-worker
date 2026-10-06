"""
Verification and Control Tools.

Phase 2: Verification Tool (assert conditions), Ask User, and Finish execution.
"""

from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel


class VerificationTool(Tool):
    name = "verification"
    description = "Verifies that two values match or a condition is true."
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "value1": {"type": "string", "description": "First value"},
            "value2": {"type": "string", "description": "Second value"},
            "condition": {
                "type": "string",
                "enum": ["equals", "not_equals", "contains"],
                "description": "Condition to check."
            }
        },
        "required": ["value1", "value2", "condition"]
    }
    
    async def execute(self, value1: str, value2: str, condition: str, **kwargs) -> ToolResult:
        if condition == "equals":
            match = (value1 == value2)
        elif condition == "not_equals":
            match = (value1 != value2)
        elif condition == "contains":
            match = (value2 in value1)
        else:
            return ToolResult(success=False, error="Unknown condition")
            
        if match:
            return ToolResult(success=True, data={"verified": True, "message": "Verification passed."})
        else:
            return ToolResult(success=False, data={"verified": False, "message": f"Verification failed. {value1} {condition} {value2} is False."})


class AskUserTool(Tool):
    name = "ask_user"
    description = "Ask the human user a question or request approval to proceed. USE THIS TOOL when the request is highly ambiguous (e.g., missing entity name), involves risky financial transactions, or when you explicitly need human clarification to proceed."
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The message to show to the user."
            }
        },
        "required": ["question"]
    }
    
    async def execute(self, question: str, **kwargs) -> ToolResult:
        # In a real async loop, this would suspend and wait for UI input.
        # For the Phase 2/3 agent loop, we will handle this specially.
        return ToolResult(success=True, data={"action": "suspend_for_input", "question": question})


class FinishTool(Tool):
    name = "finish"
    description = "End the current task and report the final result."
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "outcome": {
                "type": "string",
                "enum": ["action_done", "answered_no_action", "blocked", "cannot_determine"],
                "description": "The type of completion"
            },
            "answer": {
                "type": "string",
                "description": "The final response for the user."
            },
            "claims": {
                "type": "array",
                "description": "Any factual claims made in the answer that require verification.",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "value": {"type": ["number", "string"]},
                        "ref": {"type": "string"},
                        "path": {"type": "string"}
                    },
                    "required": ["text", "value", "ref"]
                }
            },
            "actions_taken": {
                "type": "array",
                "items": {"type": "string"}
            },
            "reason_if_not_done": {
                "type": "string"
            }
        },
        "required": ["outcome", "answer"]
    }
    
    async def execute(self, outcome: str, answer: str, claims: list = None, actions_taken: list = None, reason_if_not_done: str = None, **kwargs) -> ToolResult:
        data = {
            "action": "terminate",
            "outcome": outcome,
            "answer": answer,
            "claims": claims or [],
            "actions_taken": actions_taken or [],
            "reason_if_not_done": reason_if_not_done
        }
        return ToolResult(success=True, data=data)
