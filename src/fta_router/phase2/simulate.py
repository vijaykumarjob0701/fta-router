"""Phase-2 hybrid stack simulation orchestrator.

Honesty: cost, RAG, and tool numbers produced here are simulations under
fixed unit models and local stubs — not production measurements.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .cost_model import CostModel
from .rag_local import LocalBM25Retriever, evaluate_hit_at_k, load_corpus, load_qrels
from .tools_stub import evaluate_tools_on_rows


def _routes_from_gold(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": row.get("id"),
            "primary_action": row["primary_action"],
            "needs_rag": bool(row.get("needs_rag", False)),
            "needs_tools": bool(row.get("needs_tools", False)),
            "source": "gold",
        }
        for row in rows
    ]


def _routes_from_predictions(
    rows: Sequence[Mapping[str, Any]],
    preds: Sequence[str],
) -> list[dict[str, Any]]:
    if len(rows) != len(preds):
        raise ValueError("rows/preds length mismatch")
    out: list[dict[str, Any]] = []
    for row, pred in zip(rows, preds, strict=True):
        out.append(
            {
                "id": row.get("id"),
                "primary_action": pred,
                "needs_rag": pred == "rag",
                "needs_tools": pred == "tools",
                "source": "predicted",
                "gold_primary": row.get("primary_action"),
            }
        )
    return out


def _constant_routes(
    rows: Sequence[Mapping[str, Any]],
    *,
    primary: str,
    needs_rag: bool,
    needs_tools: bool,
    policy: str,
) -> list[dict[str, Any]]:
    return [
        {
            "id": row.get("id"),
            "primary_action": primary,
            "needs_rag": needs_rag,
            "needs_tools": needs_tools,
            "source": policy,
        }
        for row in rows
    ]


def _rag_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    if isinstance(summary, dict):
        return summary
    return {key: value for key, value in payload.items() if key != "details"}


def simulate_routes(
    rows: Sequence[Mapping[str, Any]],
    *,
    predictions: Sequence[str] | None = None,
    cost_model: CostModel | None = None,
    corpus_dir: str | Path | None = None,
    qrels_path: str | Path | None = None,
) -> dict[str, Any]:
    """Simulate cost (+ optional local RAG / tool stubs) for one split."""
    model = cost_model or CostModel()
    gold = _routes_from_gold(rows)
    policies: dict[str, tuple[list[dict[str, Any]], bool]] = {
        "gold_oracle": (gold, False),
        "always_escalate": (
            _constant_routes(
                rows,
                primary="escalate_large",
                needs_rag=False,
                needs_tools=False,
                policy="always_escalate",
            ),
            False,
        ),
        "always_rag_escalate": (
            _constant_routes(
                rows,
                primary="escalate_large",
                needs_rag=True,
                needs_tools=False,
                policy="always_rag_escalate",
            ),
            False,
        ),
    }
    if predictions is not None:
        policies["predicted"] = (_routes_from_predictions(rows, predictions), True)

    out: dict[str, Any] = {"n": len(rows)}
    for name, (routes, overhead) in policies.items():
        out[name] = model.summarise_routes(routes, include_router_overhead=overhead)

    baseline = out["always_rag_escalate"]["mean_cost"]
    for name in policies:
        mean_cost = out[name]["mean_cost"]
        out[name]["mean_cost_vs_always_rag_escalate"] = mean_cost - baseline
        out[name]["relative_cost_vs_always_rag_escalate"] = (
            (mean_cost / baseline) if baseline else None
        )

    payload: dict[str, Any] = {
        "phase": 2,
        "status": "simulation_ok",
        "honesty": {
            "cost_latency": (
                "Fixed unit cost/latency model — simulation, not a cloud bill or live API timing."
            ),
            "forbidden": "No invented EM/F1, Arena scores, or pretend live API runs.",
        },
        "cost_model_disclaimer": model.disclaimer.strip(),
        "cost_latency": out,
    }

    if corpus_dir is not None and qrels_path is not None:
        docs = load_corpus(corpus_dir)
        retriever = LocalBM25Retriever(docs)
        qrels = load_qrels(qrels_path)
        rag_all = evaluate_hit_at_k(retriever, qrels, ks=(1, 3, 5), filter_primary_rag=False)
        payload["rag_local"] = {
            "corpus_n_docs": len(docs),
            "qrels_n": len(qrels),
            "summary": _rag_summary(rag_all),
            "honesty": "Local BM25 hit@k — not live RAG answer quality.",
        }

    tools = evaluate_tools_on_rows(rows, primary_only=True)
    payload["tools_stub"] = {key: value for key, value in tools.items() if key != "details"}
    return payload


def run_phase2_simulation(
    *,
    splits: Mapping[str, tuple[Sequence[Mapping[str, Any]], Sequence[str] | None]],
    cost_model: CostModel | None = None,
    corpus_dir: str | Path | None = None,
    qrels_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run :func:`simulate_routes` for each named split."""
    model = cost_model or CostModel()
    cost_results: dict[str, Any] = {}
    tools_results: dict[str, Any] = {}
    for name, (rows, preds) in splits.items():
        result = simulate_routes(
            rows,
            predictions=preds,
            cost_model=model,
            corpus_dir=None,
            qrels_path=None,
        )
        cost_results[name] = result["cost_latency"]
        tools_results[name] = result["tools_stub"]

    payload: dict[str, Any] = {
        "phase": 2,
        "status": "simulation_ok",
        "honesty": {
            "cost_latency": (
                "Fixed unit cost/latency model — simulation, not a cloud bill or live API timing."
            ),
            "rag": "Local BM25 hit@k on a hand-built corpus/qrels — not live RAG answer quality.",
            "tools": "Deterministic stub schema validation — no real Jira/GitHub calls.",
            "forbidden": (
                "No invented EM/F1 from GPT answers, no fake Arena scores, no pretend API runs."
            ),
        },
        "cost_model_disclaimer": model.disclaimer.strip(),
        "cost_latency": cost_results,
        "tools_stub": tools_results,
    }

    if corpus_dir is not None and qrels_path is not None:
        docs = load_corpus(corpus_dir)
        retriever = LocalBM25Retriever(docs)
        qrels = load_qrels(qrels_path)
        rag_all = evaluate_hit_at_k(retriever, qrels, ks=(1, 3, 5), filter_primary_rag=False)
        rag_primary = evaluate_hit_at_k(retriever, qrels, ks=(1, 3, 5), filter_primary_rag=True)
        payload["rag_local"] = {
            "corpus_n_docs": len(docs),
            "qrels_n": len(qrels),
            "all_qrels": _rag_summary(rag_all),
            "primary_rag_only": _rag_summary(rag_primary),
        }
    return payload
