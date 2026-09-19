from __future__ import annotations

from pathlib import Path

import pytest

from fta_router import (
    DatasetError,
    load_examples,
    load_jsonl,
    summarise,
    validate_file,
    write_jsonl,
)
from fta_router.dataset import validate_rows


def test_load_and_summarise_valid_fixture(valid_jsonl: Path) -> None:
    examples = load_examples(valid_jsonl)
    assert len(examples) == 8
    actions = {example.primary_action for example in examples}
    assert actions == {"answer_small", "rag", "tools", "escalate_large"}
    summary = summarise(valid_jsonl)
    assert summary["n"] == 8
    assert summary["primary_action"]["answer_small"] == 3
    assert summary["primary_action"]["rag"] == 2
    assert summary["primary_action"]["tools"] == 2
    assert summary["primary_action"]["escalate_large"] == 1


def test_validate_file_reports_schema_and_duplicate_ids(invalid_jsonl: Path) -> None:
    errors = validate_file(invalid_jsonl)
    joined = "\n".join(errors)
    assert "needs_rag" in joined
    assert "duplicate id" in joined
    assert "primary_action" in joined


def test_load_examples_raises_on_invalid(invalid_jsonl: Path) -> None:
    with pytest.raises(DatasetError):
        load_examples(invalid_jsonl)


def test_write_and_reload_jsonl(tmp_path: Path, valid_jsonl: Path) -> None:
    rows = load_jsonl(valid_jsonl)
    out = tmp_path / "copy.jsonl"
    write_jsonl(out, rows)
    assert load_jsonl(out) == rows


def test_validate_rows_duplicate() -> None:
    rows = [
        {
            "id": "a",
            "query": "What is TCP?",
            "primary_action": "answer_small",
            "needs_rag": False,
            "needs_tools": False,
            "reasoning_level": "low",
            "rationale": "Fact.",
            "domain": "general_knowledge",
        },
        {
            "id": "a",
            "query": "What is UDP?",
            "primary_action": "answer_small",
            "needs_rag": False,
            "needs_tools": False,
            "reasoning_level": "low",
            "rationale": "Fact.",
            "domain": "general_knowledge",
        },
    ]
    errors = validate_rows(rows)
    assert any("duplicate" in error for error in errors)
