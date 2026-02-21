"""Calculator tool — math expressions, unit conversions."""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from nunuclaw.tools.base import BaseTool, ToolResult

# Safe operators for expression evaluation
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Unit conversion tables
_UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    # Length
    ("km", "miles"): 0.621371,
    ("miles", "km"): 1.60934,
    ("m", "ft"): 3.28084,
    ("ft", "m"): 0.3048,
    ("cm", "inches"): 0.393701,
    ("inches", "cm"): 2.54,
    # Weight
    ("kg", "lbs"): 2.20462,
    ("lbs", "kg"): 0.453592,
    ("g", "oz"): 0.035274,
    ("oz", "g"): 28.3495,
    # Temperature handled separately
    # Volume
    ("liters", "gallons"): 0.264172,
    ("gallons", "liters"): 3.78541,
}


def _safe_eval(node: ast.AST) -> float:
    """Safely evaluate an arithmetic expression AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    elif isinstance(node, ast.BinOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return op(left, right)
    elif isinstance(node, ast.UnaryOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        # Support math functions: sqrt, sin, cos, etc.
        if isinstance(node.func, ast.Name):
            func = getattr(math, node.func.id, None)
            if func and callable(func):
                args = [_safe_eval(a) for a in node.args]
                return func(*args)
        raise ValueError(f"Unsupported function call")
    else:
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")


class CalculatorTool(BaseTool):
    """Math calculations and unit conversions."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Calculate math expressions and convert units."

    @property
    def actions(self) -> list[str]:
        return ["compute", "convert_units"]

    async def execute(self, action: str, params: dict) -> ToolResult:
        """Execute a calculator action."""
        if action == "compute":
            return self._compute(params)
        elif action == "convert_units":
            return self._convert_units(params)
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    def _compute(self, params: dict) -> ToolResult:
        """Compute a math expression safely."""
        expr = params.get("expression", "")
        if not expr:
            return ToolResult(success=False, error="Missing 'expression' parameter")

        # Clean the expression
        expr = expr.strip()
        # Remove common natural language wrapping
        for prefix in ["what is ", "calculate ", "compute ", "solve "]:
            if expr.lower().startswith(prefix):
                expr = expr[len(prefix):]

        # Handle "x" as multiplication
        expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")

        try:
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree.body)

            # Format nicely
            if result == int(result):
                formatted = str(int(result))
            else:
                formatted = f"{result:.6g}"

            return ToolResult(success=True, data=f"{expr} = {formatted}")
        except (ValueError, SyntaxError, ZeroDivisionError) as e:
            return ToolResult(success=False, error=f"Invalid expression: {e}")

    def _convert_units(self, params: dict) -> ToolResult:
        """Convert between units."""
        value = params.get("value", 0)
        from_unit = params.get("from", "").lower()
        to_unit = params.get("to", "").lower()

        if not from_unit or not to_unit:
            return ToolResult(success=False, error="Missing 'from' or 'to' unit")

        try:
            value = float(value)
        except (ValueError, TypeError):
            return ToolResult(success=False, error=f"Invalid value: {value}")

        # Temperature special case
        if from_unit in ("c", "celsius") and to_unit in ("f", "fahrenheit"):
            result = (value * 9 / 5) + 32
            return ToolResult(success=True, data=f"{value}°C = {result:.1f}°F")
        elif from_unit in ("f", "fahrenheit") and to_unit in ("c", "celsius"):
            result = (value - 32) * 5 / 9
            return ToolResult(success=True, data=f"{value}°F = {result:.1f}°C")

        # Lookup conversion factor
        factor = _UNIT_CONVERSIONS.get((from_unit, to_unit))
        if factor is None:
            return ToolResult(
                success=False,
                error=f"Unknown conversion: {from_unit} → {to_unit}",
            )

        result = value * factor
        return ToolResult(success=True, data=f"{value} {from_unit} = {result:.4g} {to_unit}")
