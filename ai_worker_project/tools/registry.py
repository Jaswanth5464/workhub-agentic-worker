"""
Tool Registry.

Phase 2: Holds instances of all registered tools, formats them for the prompt,
and routes execution requests. Also enforces human approval limits.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from config.loader import settings as _cfg

_TOOL_TIMEOUT = 120.0

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        
    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")
        self._tools[tool.name] = tool
        
    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)
        
    def get_all_schemas(self) -> List[Dict]:
        """Get schemas for all registered tools, to inject into LLM prompts."""
        return [tool.get_schema() for tool in self._tools.values()]
        
    async def execute(self, name: str, kwargs: Dict, approval_granted: bool = False) -> ToolResult:
        """Execute a tool by name, enforcing risk checks."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
            
        # Risk enforcement: If tool requires approval for these kwargs, ensure approval_granted is True
        if getattr(tool, "requires_approval", lambda x: False)(kwargs) and not approval_granted:
            return ToolResult(
                success=False, 
                error=f"Tool {name} requires human approval. "
                      f"Please ask the user for permission before calling this tool."
            )
            
        logger.info(f"Executing tool {name} with kwargs: {kwargs} (approval_granted={approval_granted})")
        import asyncio
        try:
            exec_kwargs = {**kwargs, "approval_granted": approval_granted}
            # Wrap execution with a timeout
            return await asyncio.wait_for(tool.execute(**exec_kwargs), timeout=_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(f"Tool {name} timed out.")
            return ToolResult(success=False, error=f"TimeoutError: Tool {name} execution timed out.")
        except TypeError as e:
            logger.error(f"Tool {name} missing/invalid kwargs: {e}")
            return ToolResult(success=False, error=f"TypeError: Invalid arguments for {name}. Details: {e}")
        except PermissionError as e:
            logger.error(f"Tool {name} permission error: {e}")
            return ToolResult(success=False, error=f"PermissionError: Access denied. {e}")
        except Exception as e:
            logger.exception(f"Tool {name} raised exception")
            return ToolResult(success=False, error=f"Internal tool error: {str(e)}")
