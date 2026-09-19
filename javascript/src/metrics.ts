/** Routing evaluation metrics: accuracy, macro-F1, confusion matrix. */

import { PRIMARY_ACTIONS } from "./schema.ts";

export function confusionMatrix(
  yTrue: readonly string[],
  yPred: readonly string[],
  labels?: readonly string[],
): number[][] {
  const resolved = labels ? [...labels] : [...PRIMARY_ACTIONS];
  const index = new Map(resolved.map((label, i) => [label, i]));
  const size = resolved.length;
  const matrix = Array.from({ length: size }, () => Array.from({ length: size }, () => 0));
  if (yTrue.length !== yPred.length) {
    throw new Error("y_true and y_pred must have the same length");
  }
  for (let i = 0; i < yTrue.length; i += 1) {
    const truth = index.get(yTrue[i]);
    const pred = index.get(yPred[i]);
    if (truth !== undefined && pred !== undefined) {
      matrix[truth][pred] += 1;
    }
  }
  return matrix;
}

export function accuracyScore(yTrue: readonly string[], yPred: readonly string[]): number {
  if (yTrue.length !== yPred.length) {
    throw new Error("y_true and y_pred must have the same length");
  }
  if (!yTrue.length) {
    return 0.0;
  }
  let hits = 0;
  for (let i = 0; i < yTrue.length; i += 1) {
    if (yTrue[i] === yPred[i]) {
      hits += 1;
    }
  }
  return hits / yTrue.length;
}

export function macroF1Score(
  yTrue: readonly string[],
  yPred: readonly string[],
  labels?: readonly string[],
): number {
  const resolved = labels ? [...labels] : [...PRIMARY_ACTIONS];
  if (!resolved.length) {
    return 0.0;
  }
  const matrix = confusionMatrix(yTrue, yPred, resolved);
  const scores: number[] = [];
  const n = resolved.length;
  for (let i = 0; i < n; i += 1) {
    const truePositive = matrix[i][i];
    let falsePositive = 0;
    let falseNegative = 0;
    for (let row = 0; row < n; row += 1) {
      if (row !== i) {
        falsePositive += matrix[row][i];
      }
    }
    for (let col = 0; col < n; col += 1) {
      if (col !== i) {
        falseNegative += matrix[i][col];
      }
    }
    const precision = truePositive + falsePositive ? truePositive / (truePositive + falsePositive) : 0.0;
    const recall = truePositive + falseNegative ? truePositive / (truePositive + falseNegative) : 0.0;
    if (precision + recall === 0.0) {
      scores.push(0.0);
    } else {
      scores.push((2.0 * precision * recall) / (precision + recall));
    }
  }
  return scores.reduce((sum, value) => sum + value, 0) / scores.length;
}

export function routingMetrics(
  yTrue: readonly string[],
  yPred: readonly string[],
  labels?: readonly string[],
): {
  accuracy: number;
  macro_f1: number;
  labels: string[];
  confusion_matrix: number[][];
} {
  const resolved = labels ? [...labels] : [...PRIMARY_ACTIONS];
  return {
    accuracy: accuracyScore(yTrue, yPred),
    macro_f1: macroF1Score(yTrue, yPred, resolved),
    labels: resolved,
    confusion_matrix: confusionMatrix(yTrue, yPred, resolved),
  };
}

export function formatConfusion(cm: readonly (readonly number[])[], labels: readonly string[]): string {
  const header = "pred→\\true↓ | " + labels.map((label) => label.padStart(14, " ")).join(" | ");
  const lines = [header, "-".repeat(header.length)];
  for (let i = 0; i < labels.length; i += 1) {
    const row = labels.map((_, j) => String(cm[i][j]).padStart(14, " ")).join(" | ");
    lines.push(`${labels[i].padStart(14, " ")} | ${row}`);
  }
  return lines.join("\n");
}
