"""FTA behavioural router: FT-first 4-way action policy.

Public surface is intentionally small. Phase-2 simulation helpers live
under :mod:`fta_router.phase2`. Optional Hugging Face training lives
under :mod:`fta_router.training` (requires ``fta-router[train]``).
"""

from .baselines import (
    KeywordHeuristicBaseline,
    MajorityBaseline,
    PromptRubricSimulatedBaseline,
    available_baselines,
)
from .dataset import (
    DatasetError,
    load_examples,
    load_jsonl,
    summarise,
    validate_file,
    write_jsonl,
)
from .metrics import format_confusion, routing_metrics
from .schema import (
    DOMAINS,
    PRIMARY_ACTIONS,
    REASONING_LEVELS,
    SCHEMA_VERSION,
    RoutingExample,
    SchemaError,
    is_primary_action,
    parse_primary_action,
    validate_example,
)

__version__ = "0.1.0"

__all__ = [
    "DOMAINS",
    "PRIMARY_ACTIONS",
    "REASONING_LEVELS",
    "SCHEMA_VERSION",
    "DatasetError",
    "KeywordHeuristicBaseline",
    "MajorityBaseline",
    "PromptRubricSimulatedBaseline",
    "RoutingExample",
    "SchemaError",
    "__version__",
    "available_baselines",
    "format_confusion",
    "is_primary_action",
    "load_examples",
    "load_jsonl",
    "parse_primary_action",
    "routing_metrics",
    "summarise",
    "validate_example",
    "validate_file",
    "write_jsonl",
]
