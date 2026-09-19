"""Local mini-RAG: BM25 over a tiny markdown corpus + hit@k vs hand qrels.

Honesty: hit@k on a local corpus is **not** live RAG answer quality.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.I)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


@dataclass(frozen=True)
class CorpusDoc:
    doc_id: str
    path: str
    text: str
    tokens: tuple[str, ...]


def load_corpus(corpus_dir: str | Path) -> list[CorpusDoc]:
    corpus_dir = Path(corpus_dir)
    docs: list[CorpusDoc] = []
    for path in sorted(corpus_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append(
            CorpusDoc(
                doc_id=path.stem,
                path=str(path),
                text=text,
                tokens=tuple(tokenize(text)),
            )
        )
    if not docs:
        raise FileNotFoundError(f"no markdown docs in {corpus_dir}")
    return docs


def load_qrels(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class LocalBM25Retriever:
    """Okapi BM25 over an in-memory markdown corpus."""

    def __init__(self, docs: Sequence[CorpusDoc], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = list(docs)
        self.k1 = k1
        self.b = b
        self.doc_len = [len(doc.tokens) for doc in self.docs]
        self.avgdl = sum(self.doc_len) / max(len(self.docs), 1)
        document_frequency: Counter[str] = Counter()
        self.tf: list[Counter[str]] = []
        for doc in self.docs:
            term_freq = Counter(doc.tokens)
            self.tf.append(term_freq)
            for term in term_freq:
                document_frequency[term] += 1
        self.N = len(self.docs)
        self.idf = {
            term: math.log(1.0 + (self.N - df + 0.5) / (df + 0.5))
            for term, df in document_frequency.items()
        }

    def score(self, query: str) -> list[tuple[str, float]]:
        query_terms = tokenize(query)
        scores = [0.0] * self.N
        for term in query_terms:
            if term not in self.idf:
                continue
            idf = self.idf[term]
            for i, term_freq in enumerate(self.tf):
                freq = term_freq.get(term, 0)
                if freq == 0:
                    continue
                denom = freq + self.k1 * (1.0 - self.b + self.b * self.doc_len[i] / self.avgdl)
                scores[i] += idf * (freq * (self.k1 + 1.0) / denom)
        return sorted(
            ((self.docs[i].doc_id, scores[i]) for i in range(self.N)),
            key=lambda item: (-item[1], item[0]),
        )

    def retrieve(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        return [{"doc_id": doc_id, "score": score} for doc_id, score in self.score(query)[:k]]


def hit_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0
    return 1.0 if any(doc in relevant_set for doc in list(retrieved)[:k]) else 0.0


def evaluate_hit_at_k(
    retriever: LocalBM25Retriever,
    qrels: Sequence[Mapping[str, Any]],
    *,
    ks: Sequence[int] = (1, 3, 5),
    filter_primary_rag: bool = False,
) -> dict[str, Any]:
    rows = list(qrels)
    if filter_primary_rag:
        rows = [row for row in rows if row.get("primary_action") == "rag"]
    per_k: dict[str, list[float]] = {f"hit@{k}": [] for k in ks}
    by_split: dict[str, dict[str, list[float]]] = defaultdict(lambda: {f"hit@{k}": [] for k in ks})
    details: list[dict[str, Any]] = []
    max_k = max(ks) if ks else 5
    for row in rows:
        ranked = [doc_id for doc_id, _ in retriever.score(row["query"])]
        relevant = list(row.get("relevant_docs") or [])
        entry: dict[str, Any] = {
            "query_id": row.get("query_id"),
            "split": row.get("split"),
            "primary_action": row.get("primary_action"),
            "relevant_docs": relevant,
            "retrieved_top": ranked[:max_k],
        }
        for k in ks:
            hit = hit_at_k(ranked, relevant, k)
            per_k[f"hit@{k}"].append(hit)
            by_split[str(row.get("split") or "unknown")][f"hit@{k}"].append(hit)
            entry[f"hit@{k}"] = hit
        details.append(entry)

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    summary = {
        "n": len(rows),
        "ks": list(ks),
        "filter_primary_rag": filter_primary_rag,
        "overall": {name: _mean(vals) for name, vals in per_k.items()},
        "by_split": {
            split: {name: _mean(vals) for name, vals in metrics.items()}
            for split, metrics in by_split.items()
        },
        "retriever": "bm25_okapi_local",
        "measurement": "local_corpus_hit_at_k_vs_hand_qrels",
        "honesty": (
            "Hit@k on a tiny hand-built corpus and qrels. "
            "Not live RAG quality, not EM/F1 from LLM answers."
        ),
    }
    return {"summary": summary, "details": details}
