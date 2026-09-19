"""Routing evaluation metrics: accuracy, macro-F1, confusion matrix.

Implemented in the standard library so a core install does not pull
NumPy or scikit-learn.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .schema import PRIMARY_ACTIONS


def confusion_matrix(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> list[list[int]]:
    """Return a rows-true / cols-pred confusion matrix over *labels*."""
    labels = list(labels) if labels is not None else list(PRIMARY_ACTIONS)
    index = {label: i for i, label in enumerate(labels)}
    size = len(labels)
    matrix = [[0] * size for _ in range(size)]
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    for truth, pred in zip(y_true, y_pred, strict=True):
        if truth in index and pred in index:
            matrix[index[truth]][index[pred]] += 1
    return matrix


def accuracy_score(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Fraction of exact label matches. Empty input is 0.0."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not y_true:
        return 0.0
    hits = sum(truth == pred for truth, pred in zip(y_true, y_pred, strict=True))
    return hits / len(y_true)


def macro_f1_score(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> float:
    """Unweighted mean of per-class F1 (zero_division=0)."""
    labels = list(labels) if labels is not None else list(PRIMARY_ACTIONS)
    if not labels:
        return 0.0
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    scores: list[float] = []
    n = len(labels)
    for i in range(n):
        true_positive = matrix[i][i]
        false_positive = sum(matrix[row][i] for row in range(n) if row != i)
        false_negative = sum(matrix[i][col] for col in range(n) if col != i)
        precision = (
            true_positive / (true_positive + false_positive)
            if (true_positive + false_positive)
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if (true_positive + false_negative)
            else 0.0
        )
        if precision + recall == 0.0:
            scores.append(0.0)
        else:
            scores.append(2.0 * precision * recall / (precision + recall))
    return sum(scores) / len(scores)


def routing_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compute accuracy, macro-F1, and confusion matrix for ``primary_action``."""
    labels = list(labels) if labels is not None else list(PRIMARY_ACTIONS)
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(macro_f1_score(y_true, y_pred, labels=labels)),
        "labels": labels,
        "confusion_matrix": matrix,
    }


def format_confusion(cm: Sequence[Sequence[int]], labels: Sequence[str]) -> str:
    """Pretty-print a confusion matrix (rows = gold, columns = predicted)."""
    header = "pred→\\true↓ | " + " | ".join(f"{label:>14}" for label in labels)
    lines = [header, "-" * len(header)]
    for i, label in enumerate(labels):
        row = " | ".join(f"{cm[i][j]:14d}" for j in range(len(labels)))
        lines.append(f"{label:>14} | {row}")
    return "\n".join(lines)
