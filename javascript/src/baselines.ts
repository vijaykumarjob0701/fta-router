/** Deterministic non-neural routing baselines. None of these call an LLM API. */

import { PRIMARY_ACTIONS } from "./schema.ts";

export class MajorityBaseline {
  label = "answer_small";

  fit(labels: readonly string[]): this {
    if (!labels.length) {
      throw new Error("MajorityBaseline.fit requires at least one label");
    }
    const counts = new Map<string, number>();
    for (const label of labels) {
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    let best = labels[0];
    let bestCount = 0;
    for (const [label, count] of counts) {
      if (count > bestCount) {
        best = label;
        bestCount = count;
      }
    }
    this.label = best;
    return this;
  }

  predict(queries: Iterable<string>): string[] {
    return [...queries].map(() => this.label);
  }
}

export class KeywordHeuristicBaseline {
  static readonly TOOL_RE =
    /\b(create|open|file|schedule|comment|restart|deploy|check calendar|jira|pull request|\bpr\b|github issue|merge|page the|mute|scale)\b/i;
  static readonly RAG_RE =
    /\b(our|yesterday|last week|runbook|sla|incident|status|release notes|company|internal|what failed|confluence|wiki|postmortem)\b/i;
  static readonly ESCALATE_RE =
    /\b(tradeoff|trade-off|architect|multi-hop|root cause|plan a|compare options|design a|why did|analyse|analyze|recommend|propose a)\b/i;

  fit(_labels?: readonly string[]): this {
    return this;
  }

  predictOne(query: string): string {
    if (KeywordHeuristicBaseline.TOOL_RE.test(query)) {
      return "tools";
    }
    if (KeywordHeuristicBaseline.ESCALATE_RE.test(query)) {
      return "escalate_large";
    }
    if (KeywordHeuristicBaseline.RAG_RE.test(query)) {
      return "rag";
    }
    return "answer_small";
  }

  predict(queries: Iterable<string>): string[] {
    return [...queries].map((query) => this.predictOne(query));
  }
}

type Cue = readonly [RegExp, number];

export class PromptRubricSimulatedBaseline {
  /**
   * Deterministic simulation of a prompted 4-way router rubric.
   *
   * This is **not** an LLM API call and **not** a neural zero-shot model.
   * It encodes a documented decision order as scored regex/cue weights
   * (tools > escalate > rag > answer_small on ties). Do not cite it as a
   * large-model prompted router.
   */
  static readonly TOOL_CUES: Cue[] = [
    [
      /\b(create|file|open|schedule|book|invite|assign|merge|close|restart|deploy|scale|mute|page|acknowledge|trigger|set the feature flag|post a message|comment|upload|enable maintenance)\b/i,
      3.0,
    ],
    [/\b(jira|pagerduty|github|calendar|zendesk|linear|datadog|notion|servicenow|slack|zoom)\b/i, 2.0],
    [/\b(via the .*api|ops api|deploy api|ci api)\b/i, 2.5],
  ];
  static readonly ESCALATE_CUES: Cue[] = [
    [
      /\b(tradeoff|trade-offs|trade-off|compare|recommend|propose|design a|threat model|root-?cause|multi-week|multi-region|migration plan|decision (matrix|tree)|synthesi[sz]e|critique|reconcile|prioritis[ee]|falsif)\b/i,
      3.0,
    ],
    [/\b(plan |analyse|analyze|outline a|draft a|argue |evaluate risks)\b/i, 2.0],
    [/\b(without downtime|failure modes|with options|with risks)\b/i, 1.5],
  ];
  static readonly RAG_CUES: Cue[] = [
    [/\b(our |we |company|internal)\b/i, 2.5],
    [/\b(yesterday|last (week|night|monday|tuesday|quarter|month)|last night)\b/i, 2.5],
    [
      /\b(runbook|playbook|sla|slo|postmortem|confluence|wiki|rfc|release notes|on-call|codeowner|retention policy|what failed)\b/i,
      2.5,
    ],
    [/\b(find the|where is the|who owns|who is the|document the)\b/i, 1.5],
  ];
  static readonly ANSWER_CUES: Cue[] = [
    [
      /^(what is|what does|what do|define|explain|list |write a|how do (i|you)|convert |hello|hi[,!]|thanks|good morning)/i,
      1.5,
    ],
    [/\b(in general|typically|as a practice|briefly)\b/i, 1.0],
  ];
  static readonly SAFETY_CUES =
    /\b(phishing|bypass the company|without permission|without authorisation|fake invoice|disable security logging|hide fraudulent)\b/i;

  fit(_labels?: readonly string[]): this {
    return this;
  }

  private score(query: string, cues: readonly Cue[]): number {
    return cues.reduce((sum, [pattern, weight]) => (pattern.test(query) ? sum + weight : sum), 0);
  }

  predictOne(query: string): string {
    if (PromptRubricSimulatedBaseline.SAFETY_CUES.test(query)) {
      return "answer_small";
    }
    const scores: Record<string, number> = {
      tools: this.score(query, PromptRubricSimulatedBaseline.TOOL_CUES),
      escalate_large: this.score(query, PromptRubricSimulatedBaseline.ESCALATE_CUES),
      rag: this.score(query, PromptRubricSimulatedBaseline.RAG_CUES),
      answer_small: this.score(query, PromptRubricSimulatedBaseline.ANSWER_CUES) + 0.1,
    };
    const order = ["tools", "escalate_large", "rag", "answer_small"];
    const best = Math.max(...Object.values(scores));
    for (const action of order) {
      if (scores[action] === best && best > 0.5) {
        return action;
      }
    }
    return "answer_small";
  }

  predict(queries: Iterable<string>): string[] {
    return [...queries].map((query) => this.predictOne(query));
  }
}

export type BaselineConstructor = new () => {
  fit(labels?: readonly string[]): unknown;
  predict(queries: Iterable<string>): string[];
};

export function availableBaselines(): Record<string, BaselineConstructor> {
  return {
    majority: MajorityBaseline,
    keyword: KeywordHeuristicBaseline,
    prompt_rubric: PromptRubricSimulatedBaseline,
  };
}

if (new Set(PRIMARY_ACTIONS).size !== 4) {
  throw new Error("PRIMARY_ACTIONS must be the four-way set");
}
