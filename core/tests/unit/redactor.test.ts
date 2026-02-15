/**
 * Redactor unit tests — field-level payload redaction.
 */

import { describe, it, expect } from "vitest";
import { redactPayload } from "../../src/audit/redactor.js";
import type { RedactionRule } from "../../src/capability/types.js";

describe("redactPayload", () => {
  it("should return payload unchanged when no rules", () => {
    const payload = { name: "Alice", age: 30 };
    const result = redactPayload(payload, []);
    expect(result).toEqual({ name: "Alice", age: 30 });
  });

  it("should MASK a top-level field", () => {
    const payload = { name: "Alice", password: "secret123" };
    const rules: RedactionRule[] = [
      { json_path: "password", method: "MASK" },
    ];
    const result = redactPayload(payload, rules);
    expect(result.name).toBe("Alice");
    expect(result.password).toBe("***");
  });

  it("should DROP a top-level field", () => {
    const payload = { name: "Alice", api_key: "sk-xxx" };
    const rules: RedactionRule[] = [
      { json_path: "api_key", method: "DROP" },
    ];
    const result = redactPayload(payload, rules);
    expect(result.name).toBe("Alice");
    expect("api_key" in result).toBe(false);
  });

  it("should HASH a top-level field", () => {
    const payload = { name: "Alice", email: "alice@example.com" };
    const rules: RedactionRule[] = [
      { json_path: "email", method: "HASH" },
    ];
    const result = redactPayload(payload, rules);
    expect(result.name).toBe("Alice");
    expect(result.email).toMatch(/^hash:[a-f0-9]{16}$/);
  });

  it("should HASH deterministically", () => {
    const payload = { token: "abc123" };
    const rules: RedactionRule[] = [
      { json_path: "token", method: "HASH" },
    ];
    const r1 = redactPayload(payload, rules);
    const r2 = redactPayload(payload, rules);
    expect(r1.token).toBe(r2.token);
  });

  it("should redact nested fields using dot notation", () => {
    const payload = {
      user: { name: "Alice", password: "secret" },
      status: "ok",
    };
    const rules: RedactionRule[] = [
      { json_path: "user.password", method: "MASK" },
    ];
    const result = redactPayload(payload, rules);
    expect((result.user as any).name).toBe("Alice");
    expect((result.user as any).password).toBe("***");
    expect(result.status).toBe("ok");
  });

  it("should handle deeply nested fields", () => {
    const payload = {
      config: { auth: { token: "xyz", provider: "google" } },
    };
    const rules: RedactionRule[] = [
      { json_path: "config.auth.token", method: "DROP" },
    ];
    const result = redactPayload(payload, rules);
    const auth = (result.config as any).auth;
    expect(auth.provider).toBe("google");
    expect("token" in auth).toBe(false);
  });

  it("should skip non-existent fields gracefully", () => {
    const payload = { name: "Alice" };
    const rules: RedactionRule[] = [
      { json_path: "nonexistent", method: "MASK" },
    ];
    const result = redactPayload(payload, rules);
    expect(result).toEqual({ name: "Alice" });
  });

  it("should apply multiple rules", () => {
    const payload = { name: "Alice", password: "secret", email: "a@b.c" };
    const rules: RedactionRule[] = [
      { json_path: "password", method: "MASK" },
      { json_path: "email", method: "DROP" },
    ];
    const result = redactPayload(payload, rules);
    expect(result.name).toBe("Alice");
    expect(result.password).toBe("***");
    expect("email" in result).toBe(false);
  });

  it("should not mutate the original payload", () => {
    const payload = { name: "Alice", secret: "top-secret" };
    const rules: RedactionRule[] = [
      { json_path: "secret", method: "MASK" },
    ];
    redactPayload(payload, rules);
    expect(payload.secret).toBe("top-secret");
  });

  it("should handle non-string values for HASH", () => {
    const payload = { count: 42, data: [1, 2, 3] };
    const rules: RedactionRule[] = [
      { json_path: "count", method: "HASH" },
      { json_path: "data", method: "HASH" },
    ];
    const result = redactPayload(payload, rules);
    expect(result.count).toMatch(/^hash:[a-f0-9]{16}$/);
    expect(result.data).toMatch(/^hash:[a-f0-9]{16}$/);
  });
});
