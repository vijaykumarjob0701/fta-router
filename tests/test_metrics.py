from __future__ import annotations

from fta_router import PRIMARY_ACTIONS, format_confusion, routing_metrics
from fta_router.metrics import accuracy_score, confusion_matrix, macro_f1_score


def test_perfect_predictions() -> None:
    labels = list(PRIMARY_ACTIONS)
    metrics = routing_metrics(labels, labels)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["labels"] == labels
    assert metrics["confusion_matrix"] == [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]


def test_all_wrong_to_one_class() -> None:
    y_true = ["answer_small", "rag", "tools", "escalate_large"]
    y_pred = ["answer_small"] * 4
    metrics = routing_metrics(y_true, y_pred)
    assert metrics["accuracy"] == 0.25
    # Only answer_small has both precision and recall > 0
    assert 0.0 < metrics["macro_f1"] < 0.5


def test_empty_is_zero() -> None:
    assert accuracy_score([], []) == 0.0
    assert macro_f1_score([], [], labels=["a"]) == 0.0
    assert confusion_matrix([], [], labels=["a"]) == [[0]]


def test_format_confusion_includes_labels() -> None:
    text = format_confusion([[1, 0], [0, 2]], ["yes", "no"])
    assert "yes" in text
    assert "no" in text
    assert "2" in text
