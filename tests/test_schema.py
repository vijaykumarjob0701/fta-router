from __future__ import annotations

import pytest

from fta_router import (
    PRIMARY_ACTIONS,
    RoutingExample,
    SchemaError,
    is_primary_action,
    parse_primary_action,
    validate_example,
)


def _valid_row(**overrides: object) -> dict:
    row: dict = {
        "id": "ex-1",
        "query": "What is TCP?",
        "primary_action": "answer_small",
        "needs_rag": False,
        "needs_tools": False,
        "reasoning_level": "low",
        "rationale": "Parametric networking fact.",
        "domain": "general_knowledge",
    }
    row.update(overrides)
    return row


def test_primary_actions_are_the_four_way_set() -> None:
    assert PRIMARY_ACTIONS == ("answer_small", "rag", "tools", "escalate_large")
    assert is_primary_action("rag")
    assert not is_primary_action("teleport")


def test_parse_primary_action_rejects_unknown() -> None:
    assert parse_primary_action("tools") == "tools"
    with pytest.raises(SchemaError):
        parse_primary_action("browse")


def test_validate_example_accepts_valid_row() -> None:
    assert validate_example(_valid_row()) == []


def test_rag_requires_needs_rag() -> None:
    errors = validate_example(_valid_row(primary_action="rag", needs_rag=False))
    assert any("needs_rag" in error for error in errors)


def test_tools_requires_needs_tools() -> None:
    errors = validate_example(_valid_row(primary_action="tools", needs_tools=False))
    assert any("needs_tools" in error for error in errors)


def test_from_dict_raises_on_invalid() -> None:
    with pytest.raises(SchemaError) as exc:
        RoutingExample.from_dict(_valid_row(domain="not-a-domain"))
    assert exc.value.errors


def test_roundtrip_dict() -> None:
    example = RoutingExample.from_dict(_valid_row())
    again = RoutingExample.from_dict(example.to_dict())
    assert again == example
