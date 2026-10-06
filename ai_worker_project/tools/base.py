"""
Tool Base Classes and Risk Definitions.

Phase 2: Defines the contract for all tools. Every tool returns a predictable
ToolResult and declares its required arguments and risk level.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class RiskLevel(Enum):
    LOW = "low"         # Safe to run autonomously
    MEDIUM = "medium"   # Modifies internal state
    HIGH = "high"       # Modifies external state

class ToolResult:
    """The standard return type for all tool executions."""
    def __init__(
        self,
        ok: Optional[bool] = None,
        data: Any = None,
        error_type: Optional[str] = None,
        detail: Optional[str] = None,
        truncated: bool = False,
        total_count: Optional[int] = None,
        success: Optional[bool] = None,
        error: Optional[str] = None
    ):
        if success is not None:
            self.ok = success
        else:
            self.ok = ok or False
            
        self.data = data
        self.error_type = error_type
        
        if error is not None:
            self.detail = error
        else:
            self.detail = detail
            
        self.truncated = truncated
        self.total_count = total_count

    @property
    def success(self) -> bool:
        # Compatibility property
        return self.ok

    @property
    def error(self) -> str:
        # Compatibility property
        return self.detail or self.error_type or ""

    def format(self) -> str:
        """Format the result as a string for the LLM context."""
        if self.ok:
            if isinstance(self.data, (dict, list)):
                import json
                out = json.dumps(self.data, indent=2)
            else:
                out = str(self.data)
            if self.truncated:
                out = f"{out}\n[TRUNCATED: Showing partial results. Total count: {self.total_count}]"
            return out
        else:
            return f"Error ({self.error_type}): {self.detail}"


class Tool:
    """Base class for all agent tools."""
    
    name: str = ""
    description: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    effect: str = "read"             # "read" or "write"
    source_kind: str = "trusted"     # "trusted" or "untrusted"
    timeout_seconds: float = 30.0

    # JSON Schema representation of arguments
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given arguments."""
        raise NotImplementedError("Tools must implement execute()")
    
    def requires_approval(self, args: Dict[str, Any]) -> bool:
        """Determine if this specific execution requires human approval."""
        return self.effect == "write" or self.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]

    def preview(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Return a structured summary of the action for the human approval UI."""
        return {"tool": self.name, "args": args}

    def idempotency_key(self, args: Dict[str, Any]) -> Optional[str]:
        """Return a unique key for this operation, or None if not idempotent."""
        return None

    async def find_existing(self, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return existing record if operation was already performed, else None."""
        return None

    async def undo(self, args: Dict[str, Any], result: ToolResult) -> None:
        """Optional: Undo the effect of a write operation."""
        pass

    def validate(self, args: Dict[str, Any]) -> None:
        """Raise an exception if args are invalid (e.g. via Pydantic model)."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Return the tool definition for the LLM prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "effect": self.effect,
            "risk_level": self.risk_level.value,
            "parameters": self.parameters
        }

