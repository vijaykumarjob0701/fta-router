from __future__ import annotations

from pathlib import Path

from fta_router.cli import main
from fta_router.training import require_train_extras, train_extras_available


def test_validate_dataset_ok(valid_jsonl: Path, capsys) -> None:
    assert main(["validate-dataset", str(valid_jsonl)]) == 0
    captured = capsys.readouterr()
    assert "VALIDATION OK" in captured.out


def test_validate_dataset_fails(invalid_jsonl: Path) -> None:
    assert main(["validate-dataset", str(invalid_jsonl)]) == 1


def test_summarise_and_baseline(valid_jsonl: Path, capsys) -> None:
    assert main(["summarise", str(valid_jsonl)]) == 0
    assert main(["baseline", "keyword", "--eval", str(valid_jsonl)]) == 0
    assert (
        main(["baseline", "majority", "--train", str(valid_jsonl), "--eval", str(valid_jsonl)]) == 0
    )
    out = capsys.readouterr().out
    assert "primary_action" in out
    assert "accuracy" in out


def test_majority_without_train_fails(valid_jsonl: Path) -> None:
    assert main(["baseline", "majority", "--eval", str(valid_jsonl)]) == 2


def test_train_extras_gate() -> None:
    if train_extras_available():
        require_train_extras()
    else:
        try:
            require_train_extras()
        except ImportError as exc:
            assert "fta-router[train]" in str(exc)
        else:
            raise AssertionError("expected ImportError when extras missing")
