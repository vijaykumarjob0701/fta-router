"""Phase-2 hybrid stack simulation (cost model, local RAG, tool stubs).

These helpers are optional. They simulate a hybrid assistant; they do
**not** implement production RAG, tools, or billing.
"""

from .cost_model import DEFAULT_COST_CONFIG, CostModel, RouteCost, load_cost_model, resolve_profile
from .rag_local import LocalBM25Retriever, evaluate_hit_at_k, load_corpus
from .simulate import run_phase2_simulation, simulate_routes
from .tools_stub import ToolResult, ToolStubRuntime

__all__ = [
    "DEFAULT_COST_CONFIG",
    "CostModel",
    "LocalBM25Retriever",
    "RouteCost",
    "ToolResult",
    "ToolStubRuntime",
    "evaluate_hit_at_k",
    "load_corpus",
    "load_cost_model",
    "resolve_profile",
    "run_phase2_simulation",
    "simulate_routes",
]
