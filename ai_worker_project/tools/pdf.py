"""
PDF Reader Tool.

Phase 2: Reads text from PDF files using pypdf.
"""

import os
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel


class PDFReaderTool(Tool):
    name = "pdf_reader"
    description = "Extracts text from a local PDF file."
    risk_level = RiskLevel.LOW
    source_kind = "untrusted"
    fact_fields = ["text"]
    
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Absolute or relative path to the PDF file."
            }
        },
        "required": ["filepath"]
    }
    
    async def execute(self, filepath: str, **kwargs) -> ToolResult:
        if not HAS_PYPDF:
            return ToolResult(success=False, error="Dependency missing: pypdf is not installed.")
        if not os.path.exists(filepath):
            return ToolResult(success=False, error=f"File not found: {filepath}")
            
        try:
            reader = PdfReader(filepath)
            text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text.append(f"--- Page {i+1} ---\n{page_text}")
            
            return ToolResult(success=True, data={"text": "\n".join(text)})
        except Exception as e:
            return ToolResult(success=False, error=f"Error reading PDF: {str(e)}")
