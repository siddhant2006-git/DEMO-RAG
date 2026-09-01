import re
from typing import Any

# Deliberately not eval() — rule packs are meant to be officer-editable data,
# so applies_if is parsed as a tiny fixed grammar instead of arbitrary code.
_CONDITION_RE = re.compile(r"^\s*([\w.]+)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$")

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a is not None and float(a) >= float(b),
    "<=": lambda a, b: a is not None and float(a) <= float(b),
    ">": lambda a, b: a is not None and float(a) > float(b),
    "<": lambda a, b: a is not None and float(a) < float(b),
}


def _parse_literal(token: str) -> Any:
    token = token.strip()
    if token.lower() == "true":
        return True
    if token.lower() == "false":
        return False
    if token.startswith(("'", '"')) and token.endswith(("'", '"')):
        return token[1:-1]
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token


def evaluate_condition(expression: str, context: dict) -> bool:
    """Evaluates a single `<fact.path> <op> <literal>` expression against a
    flat context dict, e.g. "bid.claims_msme_benefit == true"."""
    match = _CONDITION_RE.match(expression)
    if not match:
        raise ValueError(f"Unsupported condition expression: {expression!r}")

    path, op, literal_token = match.groups()
    actual = context.get(path)
    expected = _parse_literal(literal_token)
    return _OPS[op](actual, expected)
