import re
from datetime import date, datetime
from typing import Any


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(str(value)).date()


def op_gte(actual: Any, expected: Any) -> bool:
    return actual is not None and float(actual) >= float(expected)


def op_lte(actual: Any, expected: Any) -> bool:
    return actual is not None and float(actual) <= float(expected)


def op_gt(actual: Any, expected: Any) -> bool:
    return actual is not None and float(actual) > float(expected)


def op_lt(actual: Any, expected: Any) -> bool:
    return actual is not None and float(actual) < float(expected)


def op_eq(actual: Any, expected: Any) -> bool:
    return actual == expected


def op_in(actual: Any, expected: Any) -> bool:
    return actual in expected


def op_regex(actual: Any, expected: Any) -> bool:
    return actual is not None and re.search(str(expected), str(actual)) is not None


def op_date_before(actual: Any, expected: Any) -> bool:
    return actual is not None and _as_date(actual) < _as_date(expected)


def op_date_after(actual: Any, expected: Any) -> bool:
    return actual is not None and _as_date(actual) > _as_date(expected)


def op_exists(actual: Any, expected: Any = None) -> bool:
    return actual is not None


OPERATORS = {
    "gte": op_gte,
    "lte": op_lte,
    "gt": op_gt,
    "lt": op_lt,
    "eq": op_eq,
    "in": op_in,
    "regex": op_regex,
    "date_before": op_date_before,
    "date_after": op_date_after,
    "exists": op_exists,
}


def evaluate(operator: str, actual: Any, expected: Any) -> bool:
    if operator not in OPERATORS:
        raise ValueError(f"Unknown operator '{operator}'. Known: {sorted(OPERATORS)}")
    return OPERATORS[operator](actual, expected)
