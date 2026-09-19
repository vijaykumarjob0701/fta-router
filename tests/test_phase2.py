from __future__ import annotations

from pathlib import Path

from fta_router.phase2 import (
    CostModel,
    LocalBM25Retriever,
    ToolStubRuntime,
    load_corpus,
    load_cost_model,
    resolve_profile,
    simulate_routes,
)
from fta_router.phase2.rag_local import evaluate_hit_at_k, load_qrels
from fta_router.phase2.tools_stub import evaluate_tools_on_rows


def test_default_cost_model_prices_routes() -> None:
    model = CostModel()
    small = model.cost_for_route("answer_small")
    large = model.cost_for_route("escalate_large")
    assert small.cost < large.cost
    assert large.large_call
    assert resolve_profile("rag", needs_tools=True) == "rag+tools"


def test_load_cost_model_json(fixtures_dir: Path) -> None:
    model = load_cost_model(fixtures_dir / "cost_model.json")
    priced = model.cost_for_route("tools")
    assert priced.cost == 3.0
    summary = model.summarise_routes(
        [{"primary_action": "answer_small"}, {"primary_action": "escalate_large"}]
    )
    assert summary["n"] == 2
    assert summary["mean_cost"] == 5.5
    assert summary["large_call_rate"] == 0.5


def test_local_bm25_hits_relevant_docs(fixtures_dir: Path) -> None:
    docs = load_corpus(fixtures_dir / "corpus")
    retriever = LocalBM25Retriever(docs)
    qrels = load_qrels(fixtures_dir / "qrels.jsonl")
    result = evaluate_hit_at_k(retriever, qrels, ks=(1, 3))
    assert result["summary"]["n"] == 2
    assert result["summary"]["overall"]["hit@1"] == 1.0


def test_tool_stub_validates_schema() -> None:
    runtime = ToolStubRuntime()
    ok = runtime.jira_create({"project": "PAY", "summary": "Timeout", "priority": "High"})
    assert ok.ok
    bad = runtime.github_comment({"repo": "not-a-repo", "issue_number": -1, "body": ""})
    assert not bad.ok
    unknown = runtime.dispatch("explode", {})
    assert unknown.errors[0].startswith("unknown tool")


def test_simulate_routes_on_fixture(valid_jsonl: Path, fixtures_dir: Path) -> None:
    from fta_router import load_jsonl

    rows = load_jsonl(valid_jsonl)
    preds = [row["primary_action"] for row in rows]
    result = simulate_routes(
        rows,
        predictions=preds,
        corpus_dir=fixtures_dir / "corpus",
        qrels_path=fixtures_dir / "qrels.jsonl",
    )
    assert result["status"] == "simulation_ok"
    assert result["cost_latency"]["n"] == 8
    assert result["tools_stub"]["n"] == 2
    assert result["tools_stub"]["schema_success_rate"] == 1.0
    tools = evaluate_tools_on_rows(rows)
    assert tools["ok"] == 2
