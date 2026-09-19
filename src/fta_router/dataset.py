"""Load and validate behavioural routing JSONL datasets."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from .schema import RoutingExample, SchemaError, validate_example


class DatasetError(ValueError):
    """Raised when a JSONL dataset cannot be loaded or fails validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "invalid dataset")


def iter_jsonl(path: str | Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield ``(line_no, row)`` for each non-empty JSONL record."""
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError([f"{path}:{line_no}: invalid JSON: {exc}"]) from exc
            if not isinstance(row, dict):
                raise DatasetError(
                    [f"{path}:{line_no}: JSON object required, got {type(row).__name__}"]
                )
            yield line_no, row


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load raw dictionaries from a JSONL file (skips blank lines)."""
    return [row for _, row in iter_jsonl(path)]


def load_examples(path: str | Path, *, validate: bool = True) -> list[RoutingExample]:
    """Load ``RoutingExample`` records from JSONL.

    When *validate* is True (default), schema and uniqueness errors raise
    ``DatasetError``.
    """
    if validate:
        errors = validate_file(path)
        if errors:
            raise DatasetError(errors)
    return [RoutingExample.from_dict(row, validate=False) for row in load_jsonl(path)]


def write_jsonl(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write mapping rows as JSONL, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=True) + "\n")


def validate_file(path: str | Path) -> list[str]:
    """Validate all rows in a JSONL file; return error messages (empty if OK)."""
    path = Path(path)
    errors: list[str] = []
    seen_ids: set[str] = set()
    try:
        stream = path.open(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]

    with stream:
        for line_no, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(row, dict):
                errors.append(f"{path.name}:{line_no}: JSON object required")
                continue
            errors.extend(validate_example(row, line_no=line_no))
            rid = row.get("id")
            if isinstance(rid, str) and rid:
                if rid in seen_ids:
                    errors.append(f"{path.name}:{line_no}: duplicate id '{rid}'")
                seen_ids.add(rid)
    return errors


def validate_rows(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """Validate in-memory rows (including duplicate ids)."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        errors.extend(validate_example(row, line_no=index))
        rid = row.get("id")
        if isinstance(rid, str) and rid:
            if rid in seen_ids:
                errors.append(f"line {index}: duplicate id '{rid}'")
            seen_ids.add(rid)
    return errors


def label_distribution(
    rows: Iterable[Mapping[str, Any]],
    field: str = "primary_action",
) -> dict[str, int]:
    """Count values of *field* across rows."""
    return dict(Counter(str(row[field]) for row in rows))


def summarise(path: str | Path) -> dict[str, Any]:
    """Return counts for a JSONL routing file."""
    rows = load_jsonl(path)
    return {
        "path": str(path),
        "n": len(rows),
        "primary_action": label_distribution(rows, "primary_action"),
        "domain": label_distribution(rows, "domain"),
        "reasoning_level": label_distribution(rows, "reasoning_level"),
    }


def examples_to_dicts(examples: Sequence[RoutingExample]) -> list[dict[str, Any]]:
    """Serialize examples back to plain dictionaries."""
    return [example.to_dict() for example in examples]


# Re-export for callers that want a single import surface.
__all__ = [
    "DatasetError",
    "SchemaError",
    "examples_to_dicts",
    "iter_jsonl",
    "label_distribution",
    "load_examples",
    "load_jsonl",
    "summarise",
    "validate_file",
    "validate_rows",
    "write_jsonl",
]
