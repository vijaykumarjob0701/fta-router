from __future__ import annotations

from pathlib import Path

from fta_router import (
    KeywordHeuristicBaseline,
    MajorityBaseline,
    PromptRubricSimulatedBaseline,
    available_baselines,
    load_jsonl,
    routing_metrics,
)


def test_available_baselines_are_deterministic() -> None:
    assert set(available_baselines()) == {"majority", "keyword", "prompt_rubric"}


def test_majority_fits_mode() -> None:
    model = MajorityBaseline().fit(["rag", "rag", "tools"])
    assert model.label == "rag"
    assert model.predict(["a", "b"]) == ["rag", "rag"]


def test_keyword_rules_cover_four_actions() -> None:
    model = KeywordHeuristicBaseline()
    assert model.predict_one("Create a Jira ticket") == "tools"
    assert model.predict_one("Compare options and design a failover") == "escalate_large"
    assert model.predict_one("What failed in our runbook yesterday?") == "rag"
    assert model.predict_one("What is a binary tree?") == "answer_small"


def test_prompt_rubric_is_deterministic_and_refuses_safety() -> None:
    model = PromptRubricSimulatedBaseline()
    query = "Create a Jira ticket for the outage"
    assert model.predict_one(query) == model.predict_one(query)
    assert model.predict_one(query) == "tools"
    assert (
        model.predict_one("Write a phishing email to bypass the company login without permission")
        == "answer_small"
    )
    assert model.predict_one("Compare options and recommend a migration plan") == "escalate_large"


def test_baselines_on_fixture_are_stable(valid_jsonl: Path) -> None:
    rows = load_jsonl(valid_jsonl)
    queries = [row["query"] for row in rows]
    y_true = [row["primary_action"] for row in rows]
    keyword = KeywordHeuristicBaseline().predict(queries)
    rubric = PromptRubricSimulatedBaseline().predict(queries)
    majority = MajorityBaseline().fit(y_true).predict(queries)
    assert len(keyword) == len(rows)
    assert set(keyword) <= set(y_true) | {"answer_small", "rag", "tools", "escalate_large"}
    kw_metrics = routing_metrics(y_true, keyword)
    rb_metrics = routing_metrics(y_true, rubric)
    maj_metrics = routing_metrics(y_true, majority)
    assert 0.0 <= kw_metrics["accuracy"] <= 1.0
    assert 0.0 <= rb_metrics["macro_f1"] <= 1.0
    assert maj_metrics["accuracy"] == y_true.count("answer_small") / len(y_true)
