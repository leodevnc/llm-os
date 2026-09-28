"""Host-owned app manifests and a bounded classical computation tool."""

import ast
import math
import operator

OS_GOAL = "Read the release checklist, calculate 18 * 7 + 24, and save a concise brief to /reports/release-brief.md."
READ_TOOLS = ["search", "read", "page_in", "page_out", "recall", "fs_list", "fs_read", "calculate", "finish"]
APPS = {
    "workspace": {"id": "workspace", "name": "Workspace", "description": "General document and memory work with reviewed writes.",
                  "tools": READ_TOOLS + ["write", "remember", "fs_write"], "write_roots": ["/notes/", "/reports/"]},
    "research": {"id": "research", "name": "Research brief", "description": "Load evidence, calculate, and write reports.",
                 "tools": READ_TOOLS + ["fs_write"], "write_roots": ["/reports/"]},
    "reviewer": {"id": "reviewer", "name": "Read-only reviewer", "description": "Inspect sources and saved files without changing them.",
                 "tools": READ_TOOLS, "write_roots": []},
}


def calculate(expression):
    """Arithmetic only; no eval, names, calls, exponentiation, or unbounded values."""
    if not isinstance(expression, str) or not 1 <= len(expression) <= 120:
        raise ValueError("Expression must contain 1–120 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("Invalid arithmetic expression") from exc
    if len(list(ast.walk(tree))) > 40:
        raise ValueError("Expression is too complex")
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in operations:
            value = operations[type(node.op)](visit(node.left), visit(node.right))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        else:
            raise ValueError("Only numbers, parentheses, and + - * / are supported")
        if not math.isfinite(value) or abs(value) > 1e12:
            raise ValueError("Arithmetic result is outside the supported range")
        return value

    try:
        return {"expression": expression, "value": visit(tree.body)}
    except (ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Arithmetic is undefined or out of range") from exc
