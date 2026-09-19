from __future__ import annotations

import fta_router


def test_version_and_exports() -> None:
    assert fta_router.__version__ == "0.1.0"
    for name in (
        "PRIMARY_ACTIONS",
        "RoutingExample",
        "load_examples",
        "routing_metrics",
        "MajorityBaseline",
        "KeywordHeuristicBaseline",
        "PromptRubricSimulatedBaseline",
        "is_primary_action",
        "validate_file",
    ):
        assert hasattr(fta_router, name)
    assert "acl_remap" not in fta_router.__all__
