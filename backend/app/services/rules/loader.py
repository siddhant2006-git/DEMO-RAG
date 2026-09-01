from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.core.errors import AppError

VALID_SEVERITIES = {"BLOCKER", "CRITICAL", "MAJOR", "MINOR"}
REQUIRED_FIELDS = ("id", "label", "severity", "weight", "fact", "operator")


@dataclass
class Rule:
    id: str
    label: str
    severity: str
    weight: float
    fact: str
    operator: str
    value: Any = None
    threshold_from: str | None = None
    source_priority: list[str] = field(default_factory=lambda: ["document"])
    applies_if: str | None = None


@dataclass
class RulePack:
    version: int
    name: str
    rules: list[Rule]


class _LineTrackingLoader(yaml.SafeLoader):
    """Attaches a __line__ key to every mapping so validation errors can point
    at the offending line in the rule pack file, not just YAML syntax errors."""


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.Node, deep: bool = False) -> dict:
    mapping = yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
    mapping["__line__"] = node.start_mark.line + 1
    return mapping


_LineTrackingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _at(raw: dict) -> str:
    line = raw.get("__line__")
    return f" (line {line})" if line else ""


def _validate_rule_dict(raw: dict, index: int) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        raise AppError(
            "INVALID_RULE_PACK",
            f"Rule at index {index} is missing required field(s): {', '.join(missing)}{_at(raw)}",
            400,
        )
    if raw["severity"] not in VALID_SEVERITIES:
        raise AppError(
            "INVALID_RULE_PACK",
            f"Rule '{raw.get('id')}' has invalid severity '{raw['severity']}'. "
            f"Must be one of {sorted(VALID_SEVERITIES)}{_at(raw)}",
            400,
        )
    if "value" not in raw and "threshold_from" not in raw and raw["operator"] != "exists":
        raise AppError(
            "INVALID_RULE_PACK",
            f"Rule '{raw['id']}' must define either 'value' or 'threshold_from'{_at(raw)}",
            400,
        )


def load_rule_pack(path: str | Path) -> RulePack:
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise AppError("RULE_PACK_NOT_FOUND", f"No rule pack at {path}", 404) from exc

    try:
        raw = yaml.load(raw_text, Loader=_LineTrackingLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f" (line {mark.line + 1})" if mark else ""
        raise AppError("INVALID_RULE_PACK", f"YAML syntax error{location}: {exc}", 400) from exc

    if not isinstance(raw, dict) or "rules" not in raw:
        raise AppError("INVALID_RULE_PACK", "Rule pack must be a mapping with a top-level 'rules' list", 400)

    rules: list[Rule] = []
    for index, raw_rule in enumerate(raw["rules"]):
        _validate_rule_dict(raw_rule, index)
        rules.append(
            Rule(
                id=raw_rule["id"],
                label=raw_rule["label"],
                severity=raw_rule["severity"],
                weight=float(raw_rule["weight"]),
                fact=raw_rule["fact"],
                operator=raw_rule["operator"],
                value=raw_rule.get("value"),
                threshold_from=raw_rule.get("threshold_from"),
                source_priority=raw_rule.get("source_priority", ["document"]),
                applies_if=raw_rule.get("applies_if"),
            )
        )

    seen_ids = set()
    for rule in rules:
        if rule.id in seen_ids:
            raise AppError("INVALID_RULE_PACK", f"Duplicate rule id '{rule.id}'", 400)
        seen_ids.add(rule.id)

    return RulePack(version=raw.get("version", 1), name=raw.get("name", path.stem), rules=rules)
