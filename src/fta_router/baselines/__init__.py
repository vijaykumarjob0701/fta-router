"""Deterministic routing baselines (no live LLM API required)."""

from .classic import (
    KeywordHeuristicBaseline,
    MajorityBaseline,
    PromptRubricSimulatedBaseline,
    available_baselines,
)

__all__ = [
    "KeywordHeuristicBaseline",
    "MajorityBaseline",
    "PromptRubricSimulatedBaseline",
    "available_baselines",
]
