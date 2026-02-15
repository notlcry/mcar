/**
 * Redactor — applies field-level redaction rules to audit payloads.
 *
 * Supports three redaction methods:
 * - MASK: Replace value with "***"
 * - HASH: Replace value with SHA-256 hash prefix
 * - DROP: Remove the field entirely
 *
 * json_path uses dot-notation (e.g. "user.password", "config.api_key").
 */

import { createHash } from "node:crypto";
import type { RedactionRule } from "../capability/types.js";

/**
 * Apply redaction rules to a payload, returning a new (redacted) copy.
 * The original payload is never mutated.
 */
export function redactPayload(
  payload: Record<string, unknown>,
  rules: readonly RedactionRule[]
): Record<string, unknown> {
  if (rules.length === 0) return payload;

  // Deep clone to avoid mutation
  let result = structuredClone(payload);

  for (const rule of rules) {
    result = applyRule(result, rule);
  }

  return result;
}

function applyRule(
  obj: Record<string, unknown>,
  rule: RedactionRule
): Record<string, unknown> {
  const parts = rule.json_path.split(".");
  return applyAtPath(obj, parts, 0, rule.method);
}

function applyAtPath(
  obj: Record<string, unknown>,
  parts: string[],
  index: number,
  method: RedactionRule["method"]
): Record<string, unknown> {
  if (index >= parts.length) return obj;

  const key = parts[index];
  if (!(key in obj)) return obj;

  // Last segment — apply redaction
  if (index === parts.length - 1) {
    const copy = { ...obj };
    switch (method) {
      case "MASK":
        copy[key] = "***";
        break;
      case "HASH":
        copy[key] = hashValue(obj[key]);
        break;
      case "DROP":
        delete copy[key];
        break;
    }
    return copy;
  }

  // Intermediate segment — recurse into nested object
  const nested = obj[key];
  if (typeof nested !== "object" || nested === null || Array.isArray(nested)) {
    return obj;
  }

  return {
    ...obj,
    [key]: applyAtPath(nested as Record<string, unknown>, parts, index + 1, method),
  };
}

function hashValue(value: unknown): string {
  const str = typeof value === "string" ? value : JSON.stringify(value);
  const hash = createHash("sha256").update(str).digest("hex");
  return `hash:${hash.slice(0, 16)}`;
}
