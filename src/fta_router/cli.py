"""Command-line interface for ``fta-router``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .baselines import available_baselines
from .dataset import load_jsonl, summarise, validate_file
from .metrics import format_confusion, routing_metrics


def _cmd_validate(args: argparse.Namespace) -> int:
    all_errors: list[str] = []
    for path in args.paths:
        if not path.exists():
            all_errors.append(f"missing file: {path}")
            continue
        errors = validate_file(path)
        all_errors.extend(errors)
        summary = summarise(path)
        print(f"== {path}")
        print(f"   n={summary['n']}")
        print(f"   primary_action={summary['primary_action']}")
        print(f"   domain={summary['domain']}")
        print(f"   reasoning_level={summary['reasoning_level']}")
        if args.strict and summary["n"] == 0:
            all_errors.append(f"{path}: empty file")
    if all_errors:
        print("\nVALIDATION FAILED", file=sys.stderr)
        for error in all_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("\nVALIDATION OK")
    return 0


def _cmd_summarise(args: argparse.Namespace) -> int:
    print(json.dumps(summarise(args.path), indent=2))
    return 0


def _cmd_baseline(args: argparse.Namespace) -> int:
    constructors = available_baselines()
    model = constructors[args.name]()
    eval_rows = load_jsonl(args.eval)
    if args.name == "majority":
        if args.train is None:
            print("majority baseline requires --train so the mode can be fit", file=sys.stderr)
            return 2
        train_rows = load_jsonl(args.train)
        model.fit([row["primary_action"] for row in train_rows])
    elif hasattr(model, "fit"):
        model.fit()
    preds = model.predict([row["query"] for row in eval_rows])
    y_true = [row["primary_action"] for row in eval_rows]
    metrics = routing_metrics(y_true, preds)
    printable = {key: value for key, value in metrics.items() if key != "confusion_matrix"}
    printable["method"] = args.name
    printable["n_eval"] = len(eval_rows)
    if args.name == "majority":
        printable["majority_label"] = model.label
    if args.name == "prompt_rubric":
        printable["honesty"] = (
            "Deterministic labeling-rubric simulation; NOT an LLM API prompted router."
        )
    print(json.dumps(printable, indent=2))
    print(format_confusion(metrics["confusion_matrix"], metrics["labels"]))
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    from .training import require_train_extras, train_text_classifier

    try:
        require_train_extras()
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    result = train_text_classifier(
        args.train,
        args.eval,
        model_name=args.model,
        output_dir=args.output_dir,
        num_epochs=args.epochs,
    )
    printable = {key: value for key, value in result.items() if key != "confusion_matrix"}
    print(json.dumps(printable, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fta-router",
        description="FT-first hybrid behavioural router utilities.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-dataset", help="Validate routing JSONL against schema 1.0")
    validate.add_argument("paths", nargs="+", type=Path, help="JSONL files to validate")
    validate.add_argument("--strict", action="store_true", help="Fail if a file has zero rows")
    validate.set_defaults(func=_cmd_validate)

    summary = sub.add_parser("summarise", help="Print label counts for a JSONL file")
    summary.add_argument("path", type=Path)
    summary.set_defaults(func=_cmd_summarise)

    baseline = sub.add_parser("baseline", help="Evaluate a deterministic routing baseline")
    baseline.add_argument("name", choices=sorted(available_baselines()))
    baseline.add_argument("--eval", type=Path, required=True, help="Eval JSONL")
    baseline.add_argument("--train", type=Path, default=None, help="Train JSONL (majority only)")
    baseline.set_defaults(func=_cmd_baseline)

    train = sub.add_parser("train", help="Fine-tune a text classifier (requires [train] extra)")
    train.add_argument("--train", type=Path, required=True)
    train.add_argument("--eval", type=Path, required=True)
    train.add_argument("--model", default="distilbert-base-uncased")
    train.add_argument("--output-dir", type=Path, default=Path("outputs/router"))
    train.add_argument("--epochs", type=int, default=3)
    train.set_defaults(func=_cmd_train)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
