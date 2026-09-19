"""Deterministic fake tools with schema validation (no real API calls)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    tool: str
    ok: bool
    errors: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)


class ToolStubRuntime:
    """In-memory Jira/GitHub stubs used for schema-success simulation."""

    PRIORITY_ENUM = ("Lowest", "Low", "Medium", "High", "Highest")
    REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

    def __init__(self) -> None:
        self.calls: list[ToolResult] = []

    def jira_create(self, args: Mapping[str, Any]) -> ToolResult:
        errors: list[str] = []
        if not isinstance(args.get("project"), str) or not str(args.get("project")).strip():
            errors.append("project: required non-empty string")
        if not isinstance(args.get("summary"), str) or not str(args.get("summary")).strip():
            errors.append("summary: required non-empty string")
        if "priority" in args and args["priority"] is not None:
            if args["priority"] not in self.PRIORITY_ENUM:
                errors.append(f"priority: must be one of {self.PRIORITY_ENUM}")
        if "labels" in args and args["labels"] is not None:
            if not isinstance(args["labels"], list) or not all(
                isinstance(item, str) for item in args["labels"]
            ):
                errors.append("labels: must be a list of strings")
        ok = not errors
        payload = {
            "issue_key": f"{str(args.get('project', 'X')).upper()}-STUB-1" if ok else None,
            "status": "created_stub" if ok else "rejected",
        }
        result = ToolResult(tool="jira_create", ok=ok, errors=errors, payload=payload)
        self.calls.append(result)
        return result

    def github_comment(self, args: Mapping[str, Any]) -> ToolResult:
        errors: list[str] = []
        repo = args.get("repo")
        if not isinstance(repo, str) or not self.REPO_RE.match(repo):
            errors.append("repo: required as 'owner/name'")
        issue = args.get("issue_number")
        if not isinstance(issue, int) or issue <= 0:
            errors.append("issue_number: required positive int")
        body = args.get("body")
        if not isinstance(body, str) or not body.strip():
            errors.append("body: required non-empty string")
        ok = not errors
        payload = {
            "comment_id": 9001 if ok else None,
            "status": "created_stub" if ok else "rejected",
        }
        result = ToolResult(tool="github_comment", ok=ok, errors=errors, payload=payload)
        self.calls.append(result)
        return result

    def dispatch(self, tool: str, args: Mapping[str, Any]) -> ToolResult:
        if tool == "jira_create":
            return self.jira_create(args)
        if tool == "github_comment":
            return self.github_comment(args)
        result = ToolResult(tool=tool, ok=False, errors=[f"unknown tool: {tool}"])
        self.calls.append(result)
        return result


def infer_tool_args_from_query(query: str) -> tuple[str, dict[str, Any]]:
    """Heuristic argument filler for stub evaluation only."""
    lowered = query.lower()
    if re.search(r"\b(github|pull request|\bpr\b|comment on)\b", lowered):
        repo_match = re.search(r"(github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", query)
        repo = repo_match.group(2) if repo_match else "acme/platform-mono"
        number_match = re.search(r"#(\d+)", query) or re.search(r"\bissue\s+(\d+)", lowered)
        issue_number = int(number_match.group(1)) if number_match else 42
        return "github_comment", {
            "repo": repo,
            "issue_number": issue_number,
            "body": f"Stub comment regarding: {query[:180]}",
        }
    project = "PAY"
    if re.search(r"\bmobile\b", lowered):
        project = "MOB"
    elif re.search(r"\bplatform\b", lowered):
        project = "PLAT"
    elif re.search(r"\bsearch\b", lowered):
        project = "SRCH"
    summary = query.strip()
    if len(summary) > 120:
        summary = summary[:117] + "..."
    return "jira_create", {
        "project": project,
        "summary": summary or "untitled stub",
        "priority": "Medium",
        "labels": ["phase2-stub"],
    }


def evaluate_tools_on_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    primary_only: bool = True,
) -> dict[str, Any]:
    runtime = ToolStubRuntime()
    selected: list[Mapping[str, Any]] = []
    for row in rows:
        if primary_only:
            if row.get("primary_action") == "tools":
                selected.append(row)
        elif row.get("needs_tools") or row.get("primary_action") == "tools":
            selected.append(row)
    results: list[dict[str, Any]] = []
    ok_n = 0
    for row in selected:
        tool, args = infer_tool_args_from_query(str(row["query"]))
        result = runtime.dispatch(tool, args)
        if result.ok:
            ok_n += 1
        results.append(
            {
                "id": row.get("id"),
                "query": row.get("query"),
                "tool": tool,
                "args": args,
                "ok": result.ok,
                "errors": result.errors,
            }
        )
    n = len(selected)
    buckets: dict[str, list[bool]] = {}
    for row in results:
        buckets.setdefault(str(row["tool"]), []).append(bool(row["ok"]))
    by_tool: dict[str, dict[str, float | int]] = {}
    for tool, oks in buckets.items():
        count = len(oks)
        ok = sum(1 for item in oks if item)
        rate = (ok / count) if count else 0.0
        by_tool[tool] = {"n": count, "ok": ok, "schema_success_rate": rate}
    return {
        "n": n,
        "schema_success_rate": (ok_n / n) if n else 0.0,
        "ok": ok_n,
        "failed": n - ok_n,
        "by_tool": by_tool,
        "measurement": "deterministic_tool_stub_schema_validation",
        "honesty": (
            "Fake tools only; success = schema validation of heuristically filled args. "
            "No real Jira/GitHub API calls."
        ),
        "details": results,
    }
