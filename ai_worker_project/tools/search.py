"""
Search Tools.

Phase 2: File Search and Web Search.
"""

import os
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel


class FileSearchTool(Tool):
    name = "file_search"
    description = "Searches for files in a given directory and returns their names."
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "The directory path to search in."
            },
            "extension": {
                "type": "string",
                "description": "Optional file extension to filter by (e.g. '.pdf')."
            }
        },
        "required": ["directory"]
    }
    
    async def execute(self, directory: str, extension: str = None, **kwargs) -> ToolResult:
        if not os.path.isdir(directory):
            return ToolResult(success=False, error=f"Directory not found: {directory}")
            
        try:
            files = []
            for root, _, filenames in os.walk(directory):
                for name in filenames:
                    if not extension or name.endswith(extension):
                        files.append(os.path.join(root, name))
            return ToolResult(success=True, data={"files": files})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


