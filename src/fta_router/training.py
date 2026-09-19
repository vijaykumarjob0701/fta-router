"""Optional Hugging Face training helpers.

Install extras first::

    pip install "fta-router[train]"

This module is imported by the CLI. Heavy dependencies (torch,
transformers, datasets, accelerate) are imported only inside
:func:`train_text_classifier`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .dataset import load_jsonl
from .metrics import routing_metrics
from .schema import PRIMARY_ACTIONS

TRAIN_EXTRA_PACKAGES = ("torch", "transformers", "datasets", "accelerate")


def train_extras_available() -> bool:
    """Return True when the ``[train]`` extra can be imported."""
    for name in TRAIN_EXTRA_PACKAGES:
        try:
            __import__(name)
        except ImportError:
            return False
    return True


def require_train_extras() -> None:
    """Raise ``ImportError`` with an install hint if extras are missing."""
    missing: list[str] = []
    for name in TRAIN_EXTRA_PACKAGES:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if missing:
        raise ImportError(
            "Training requires the optional [train] extra "
            f"(missing: {', '.join(missing)}). Install with:\n"
            '  pip install "fta-router[train]"'
        )


def train_text_classifier(
    train_path: str | Path,
    eval_path: str | Path,
    *,
    model_name: str = "distilbert-base-uncased",
    output_dir: str | Path = "outputs/router",
    text_field: str = "query",
    label_field: str = "primary_action",
    labels: Sequence[str] | None = None,
    num_epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    weight_decay: float = 0.01,
    max_length: int = 128,
    warmup_ratio: float = 0.1,
    seed: int = 42,
    training: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fine-tune a sequence classifier on ``primary_action`` labels.

    Returns measured eval routing metrics. Does not invent scores.
    """
    require_train_extras()

    import inspect
    import math

    import numpy as np
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
    )

    overrides = dict(training or {})
    num_epochs = int(overrides.get("num_epochs", num_epochs))
    batch_size = int(overrides.get("batch_size", batch_size))
    learning_rate = float(overrides.get("learning_rate", learning_rate))
    weight_decay = float(overrides.get("weight_decay", weight_decay))
    max_length = int(overrides.get("max_length", max_length))
    warmup_ratio = float(overrides.get("warmup_ratio", warmup_ratio))
    seed = int(overrides.get("seed", seed))

    action_labels = list(labels) if labels is not None else list(PRIMARY_ACTIONS)
    label2id = {label: i for i, label in enumerate(action_labels)}
    id2label = {i: label for i, label in enumerate(action_labels)}

    train_rows = load_jsonl(train_path)
    eval_rows = load_jsonl(eval_path)

    def to_hf(rows: Sequence[Mapping[str, Any]]) -> Dataset:
        return Dataset.from_dict(
            {
                "text": [row[text_field] for row in rows],
                "label": [label2id[str(row[label_field])] for row in rows],
            }
        )

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize(batch: Mapping[str, Any]) -> Mapping[str, Any]:
        return tokenizer(batch["text"], truncation=True, max_length=max_length)

    train_ds = to_hf(train_rows).map(tokenize, batched=True)
    eval_ds = to_hf(eval_rows).map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(action_labels),
        id2label=id2label,
        label2id=label2id,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ta_params = inspect.signature(TrainingArguments.__init__).parameters
    strategy_key = "eval_strategy" if "eval_strategy" in ta_params else "evaluation_strategy"
    steps_per_epoch = max(1, math.ceil(len(train_rows) / batch_size))
    total_steps = max(1, steps_per_epoch * num_epochs)
    warmup_steps = int(total_steps * warmup_ratio)
    targs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "learning_rate": learning_rate,
        "per_device_train_batch_size": batch_size,
        "per_device_eval_batch_size": batch_size,
        "num_train_epochs": num_epochs,
        "weight_decay": weight_decay,
        "save_strategy": "epoch",
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_macro_f1",
        "greater_is_better": True,
        "seed": seed,
        "report_to": [],
        strategy_key: "epoch",
    }
    if "warmup_ratio" in ta_params:
        targs["warmup_ratio"] = warmup_ratio
    elif "warmup_steps" in ta_params:
        targs["warmup_steps"] = warmup_steps
    targs = {key: value for key, value in targs.items() if key in ta_params or key == strategy_key}
    args = TrainingArguments(**targs)

    def compute_metrics(eval_pred: Any) -> dict[str, float]:
        logits, label_ids = eval_pred
        pred_ids = np.argmax(logits, axis=-1)
        y_true = [id2label[int(i)] for i in label_ids]
        y_pred = [id2label[int(i)] for i in pred_ids]
        metrics = routing_metrics(y_true, y_pred, labels=action_labels)
        return {"accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"]}

    trainer_kwargs: dict[str, Any] = {
        "model": model,
        "args": args,
        "train_dataset": train_ds,
        "eval_dataset": eval_ds,
        "data_collator": DataCollatorWithPadding(tokenizer),
        "compute_metrics": compute_metrics,
    }
    trainer_params = inspect.signature(Trainer.__init__).parameters
    if "processing_class" in trainer_params:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_params:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = Trainer(**trainer_kwargs)
    trainer.train()
    trainer_eval = trainer.evaluate()
    trainer.save_model(str(output_dir / "best"))

    pred_out = trainer.predict(eval_ds)
    pred_ids = np.argmax(pred_out.predictions, axis=-1)
    y_true = [id2label[int(i)] for i in pred_out.label_ids]
    y_pred = [id2label[int(i)] for i in pred_ids]
    measured = routing_metrics(y_true, y_pred, labels=action_labels)
    return {
        "method": "ft_text_classifier",
        "model_name": model_name,
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "epochs": num_epochs,
        "seed": seed,
        "accuracy": measured["accuracy"],
        "macro_f1": measured["macro_f1"],
        "labels": measured["labels"],
        "confusion_matrix": measured["confusion_matrix"],
        "trainer_eval": {
            key: float(value) if hasattr(value, "item") else value
            for key, value in trainer_eval.items()
        },
        "output_dir": str(output_dir / "best"),
        "status": "ok",
    }
