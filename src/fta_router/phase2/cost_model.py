"""Route → cost/latency simulation under fixed unit rates.

Honesty: these are **illustrative unit rates**, not a cloud bill, not
measured production latency, and not claimed research results.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_COST_CONFIG: dict[str, Any] = {
    "disclaimer": (
        "Fixed illustrative unit costs and latencies — simulation only, "
        "not a cloud bill or live API timing."
    ),
    "router_overhead": {"cost": 0.0001, "latency_ms": 15.0},
    "actions": {
        "answer_small": {"cost": 0.0002, "latency_ms": 80.0, "large_call": False},
        "rag": {"cost": 0.0008, "latency_ms": 220.0, "large_call": False},
        "tools": {"cost": 0.0006, "latency_ms": 180.0, "large_call": False},
        "escalate_large": {"cost": 0.012, "latency_ms": 1200.0, "large_call": True},
    },
    "combinations": {
        "rag+tools": {"cost": 0.0012, "latency_ms": 320.0, "large_call": False},
        "escalate_large+rag": {"cost": 0.013, "latency_ms": 1400.0, "large_call": True},
        "escalate_large+tools": {"cost": 0.0125, "latency_ms": 1350.0, "large_call": True},
        "escalate_large+rag+tools": {"cost": 0.0135, "latency_ms": 1550.0, "large_call": True},
    },
}


def resolve_profile(
    primary: str,
    needs_rag: bool = False,
    needs_tools: bool = False,
) -> str:
    """Map a 4-way action plus flags onto a cost-profile name."""
    if primary == "answer_small":
        return "answer_small"
    if primary == "rag":
        return "rag+tools" if needs_tools else "rag"
    if primary == "tools":
        return "rag+tools" if needs_rag else "tools"
    if primary == "escalate_large":
        if needs_rag and needs_tools:
            return "escalate_large+rag+tools"
        if needs_rag:
            return "escalate_large+rag"
        if needs_tools:
            return "escalate_large+tools"
        return "escalate_large"
    raise ValueError(f"unknown primary_action: {primary}")


@dataclass(frozen=True)
class RouteCost:
    profile: str
    cost: float
    latency_ms: float
    large_call: bool


class CostModel:
    """Lookup table for simulated route cost and latency."""

    def __init__(self, cfg: Mapping[str, Any] | None = None) -> None:
        cfg = dict(cfg) if cfg is not None else dict(DEFAULT_COST_CONFIG)
        self.cfg = cfg
        self.actions = dict(cfg["actions"])
        self.combinations = dict(cfg.get("combinations") or {})
        self.router_overhead = dict(cfg.get("router_overhead") or {"cost": 0.0, "latency_ms": 0.0})
        self.cascade_policies = dict(cfg.get("cascade_policies") or {})
        self.disclaimer = str(cfg.get("disclaimer") or DEFAULT_COST_CONFIG["disclaimer"])

    def lookup(self, profile: str) -> RouteCost:
        if profile in self.actions:
            row = self.actions[profile]
        elif profile in self.combinations:
            row = self.combinations[profile]
        else:
            raise KeyError(f"cost profile not in model: {profile}")
        return RouteCost(
            profile=profile,
            cost=float(row["cost"]),
            latency_ms=float(row["latency_ms"]),
            large_call=bool(row.get("large_call", profile.startswith("escalate"))),
        )

    def cost_for_route(
        self,
        primary: str,
        needs_rag: bool = False,
        needs_tools: bool = False,
        *,
        include_router_overhead: bool = False,
    ) -> RouteCost:
        profile = resolve_profile(primary, needs_rag, needs_tools)
        base = self.lookup(profile)
        if not include_router_overhead:
            return base
        return RouteCost(
            profile=profile,
            cost=base.cost + float(self.router_overhead.get("cost", 0.0)),
            latency_ms=base.latency_ms + float(self.router_overhead.get("latency_ms", 0.0)),
            large_call=base.large_call,
        )

    def summarise_routes(
        self,
        routes: Sequence[Mapping[str, Any]],
        *,
        include_router_overhead: bool = False,
    ) -> dict[str, Any]:
        costs: list[float] = []
        latencies: list[float] = []
        large = 0
        profiles: dict[str, int] = {}
        for route in routes:
            priced = self.cost_for_route(
                str(route["primary_action"]),
                bool(route.get("needs_rag", False)),
                bool(route.get("needs_tools", False)),
                include_router_overhead=include_router_overhead,
            )
            costs.append(priced.cost)
            latencies.append(priced.latency_ms)
            if priced.large_call:
                large += 1
            profiles[priced.profile] = profiles.get(priced.profile, 0) + 1
        n = len(routes)
        if n == 0:
            return {
                "n": 0,
                "mean_cost": 0.0,
                "large_call_rate": 0.0,
                "latency_p50_ms": 0.0,
                "latency_p95_ms": 0.0,
                "profile_counts": {},
                "measurement": "simulation_under_fixed_unit_model",
            }
        sorted_lat = sorted(latencies)
        return {
            "n": n,
            "mean_cost": sum(costs) / n,
            "total_cost": sum(costs),
            "large_call_rate": large / n,
            "latency_p50_ms": _percentile(sorted_lat, 50),
            "latency_p95_ms": _percentile(sorted_lat, 95),
            "mean_latency_ms": sum(latencies) / n,
            "profile_counts": profiles,
            "measurement": "simulation_under_fixed_unit_model",
            "disclaimer": self.disclaimer.strip(),
        }


def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    floor = int(k)
    ceil = min(floor + 1, len(sorted_vals) - 1)
    if floor == ceil:
        return float(sorted_vals[floor])
    return float(sorted_vals[floor] + (sorted_vals[ceil] - sorted_vals[floor]) * (k - floor))


def load_cost_model(path: str | Path) -> CostModel:
    """Load a cost model from JSON, or YAML if PyYAML is installed."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "Loading YAML cost models requires PyYAML. "
                "Pass a .json file or construct CostModel(config_dict) instead."
            ) from exc
        cfg = yaml.safe_load(text)
    else:
        cfg = json.loads(text)
    if not isinstance(cfg, dict):
        raise ValueError(f"cost model file must contain an object: {path}")
    return CostModel(cfg)
