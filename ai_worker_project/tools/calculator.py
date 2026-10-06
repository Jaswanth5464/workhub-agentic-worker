"""
Calculator Tool.

Phase 2: Safely evaluates math expressions. Used for verifying record totals
or calculating taxes.
"""

import ast
import operator
from typing import Any, Dict

from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel

# Safe math operators mapping
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def safe_eval_expr(node):
    """Recursively evaluate the AST for safe math expressions."""
    if isinstance(node, ast.Num):  # <python3.8
        return node.n
    elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = safe_eval_expr(node.left)
        right = safe_eval_expr(node.right)
        op = type(node.op)
        if op in OPERATORS:
            return OPERATORS[op](left, right)
        else:
            raise ValueError(f"Unsupported operator: {op}")
    elif isinstance(node, ast.UnaryOp):
        operand = safe_eval_expr(node.operand)
        op = type(node.op)
        if op in OPERATORS:
            return OPERATORS[op](operand)
        else:
            raise ValueError(f"Unsupported operator: {op}")
    else:
        raise ValueError(f"Unsupported expression node: {type(node)}")


class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluates basic math expressions (e.g. '120 * 0.18' or '500 + 100'). Supports +, -, *, /."
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The math expression to evaluate."
            }
        },
        "required": ["expression"]
    }
    
    async def execute(self, expression: str, **kwargs) -> ToolResult:
        try:
            tree = ast.parse(expression, mode='eval')
            result = safe_eval_expr(tree.body)
            return ToolResult(success=True, data={"result": result})
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to calculate: {str(e)}")
