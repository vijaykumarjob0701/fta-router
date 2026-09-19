from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def valid_jsonl(fixtures_dir: Path) -> Path:
    return fixtures_dir / "routing_valid.jsonl"


@pytest.fixture
def invalid_jsonl(fixtures_dir: Path) -> Path:
    return fixtures_dir / "routing_invalid.jsonl"
