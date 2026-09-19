"""4-way behavioural routing schema (version 1.0)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Final

SCHEMA_VERSION: Final = "1.0"

PRIMARY_ACTIONS: Final[tuple[str, ...]] = (
    "answer_small",
    "rag",
    "tools",
    "escalate_large",
)
REASONING_LEVELS: Final[tuple[str, ...]] = ("low", "medium", "high")
DOMAINS: Final[tuple[str, ...]] = (
    "general_knowledge",
    "company_current",
    "tool_action",
    "multi_hop_planning",
    "ambiguous",
    "safety_mild",
    "open_domain_qa",
)

REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "id",
    "query",
    "primary_action",
    "needs_rag",
    "needs_tools",
    "reasoning_level",
    "rationale",
    "domain",
)


class SchemaError(ValueError):
    """Raised when a routing record fails schema validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "invalid routing example")


def is_primary_action(value: object) -> bool:
    """Return True if *value* is one of the four routing actions."""
    return value in PRIMARY_ACTIONS


def parse_primary_action(value: str) -> str:
    """Return *value* if it is a valid primary action, else raise ``SchemaError``."""
    if not is_primary_action(value):
        raise SchemaError([f"primary_action '{value}' not in {PRIMARY_ACTIONS}"])
    return value


@dataclass(frozen=True)
class RoutingExample:
    """One labelled behavioural routing decision."""

    id: str
    query: str
    primary_action: str
    needs_rag: bool
    needs_tools: bool
    reasoning_level: str
    rationale: str
    domain: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: Mapping[str, Any], *, validate: bool = True) -> RoutingExample:
        if validate:
            errors = validate_example(row)
            if errors:
                raise SchemaError(errors)
        return cls(
            id=str(row["id"]),
            query=str(row["query"]),
            primary_action=str(row["primary_action"]),
            needs_rag=bool(row["needs_rag"]),
            needs_tools=bool(row["needs_tools"]),
            reasoning_level=str(row["reasoning_level"]),
            rationale=str(row["rationale"]),
            domain=str(row["domain"]),
        )


def validate_example(row: Mapping[str, Any], *, line_no: int | None = None) -> list[str]:
    """Return a list of validation error strings (empty if valid)."""
    prefix = f"line {line_no}: " if line_no is not None else ""
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"{prefix}missing required field '{field}'")
    if errors:
        return errors

    if not isinstance(row["id"], str) or not row["id"].strip():
        errors.append(f"{prefix}id must be a non-empty string")
    if not isinstance(row["query"], str) or not row["query"].strip():
        errors.append(f"{prefix}query must be a non-empty string")
    if not isinstance(row["rationale"], str) or not row["rationale"].strip():
        errors.append(f"{prefix}rationale must be a non-empty string")

    action = row["primary_action"]
    if action not in PRIMARY_ACTIONS:
        errors.append(f"{prefix}primary_action '{action}' not in {PRIMARY_ACTIONS}")

    if not isinstance(row["needs_rag"], bool):
        errors.append(f"{prefix}needs_rag must be bool, got {type(row['needs_rag']).__name__}")
    if not isinstance(row["needs_tools"], bool):
        errors.append(f"{prefix}needs_tools must be bool, got {type(row['needs_tools']).__name__}")

    level = row["reasoning_level"]
    if level not in REASONING_LEVELS:
        errors.append(f"{prefix}reasoning_level '{level}' not in {REASONING_LEVELS}")

    domain = row["domain"]
    if domain not in DOMAINS:
        errors.append(f"{prefix}domain '{domain}' not in {DOMAINS}")

    if action == "rag" and row.get("needs_rag") is not True:
        errors.append(f"{prefix}primary_action=rag requires needs_rag=true")
    if action == "tools" and row.get("needs_tools") is not True:
        errors.append(f"{prefix}primary_action=tools requires needs_tools=true")

    return errors
