/**
 * Web API integration tests.
 *
 * Tests REST endpoints with a real Express server.
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { WebServer } from "../../src/web/server.js";
import { StateService } from "../../src/state/state-service.js";
import { CapabilityRegistry } from "../../src/capability/registry.js";
import { CapabilityExecutor } from "../../src/capability/executor.js";
import { PolicyEngine } from "../../src/safety/policy-engine.js";
import { StopHandler } from "../../src/safety/stop-handler.js";
import { MemoryService } from "../../src/memory/memory-service.js";
import { SessionController } from "../../src/orchestrator/session-controller.js";
import { ActionDispatcher } from "../../src/orchestrator/action-dispatcher.js";
import { AuditLogger } from "../../src/audit/audit-logger.js";

const TEST_PORT = 18080;

// Minimal mocks
const mockBridge = {
  broadcastStop: async () => {},
  onEvent: () => () => {},
  onRegister: () => () => {},
  getRegisteredModules: () => ["mock"],
} as any;

const mockAgent = {
  prompt: async () => {},
  subscribe: () => () => {},
} as any;

describe("Web API", () => {
  let server: WebServer;
  let stateService: StateService;
  let memoryService: MemoryService;
  let auditLogger: AuditLogger;

  beforeAll(async () => {
    stateService = new StateService();
    auditLogger = new AuditLogger();
    const stopHandler = new StopHandler(mockBridge, { estopCooldownMs: 2000 });
    memoryService = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
    const registry = new CapabilityRegistry(mockBridge);
    const executor = new CapabilityExecutor(registry);
    const policyEngine = new PolicyEngine(stopHandler, stateService, memoryService);
    const session = new SessionController(stateService, stopHandler);
    const dispatcher = new ActionDispatcher(session, mockAgent, auditLogger, stopHandler);

    server = new WebServer(
      { port: TEST_PORT, host: "127.0.0.1" },
      stateService,
      registry,
      executor,
      policyEngine,
      memoryService,
      stopHandler,
      dispatcher,
      session,
      mockBridge,
      auditLogger
    );

    await server.start();
  });

  afterAll(async () => {
    memoryService.close();
    await server.stop();
  });

  const baseUrl = `http://127.0.0.1:${TEST_PORT}`;

  it("GET /api/status should return state snapshot", async () => {
    const res = await fetch(`${baseUrl}/api/status`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.session).toBe("IDLE");
    expect(body.mode).toBe("normal");
    expect(body.apiStatus).toBe("online");
    expect(body.registeredModules).toEqual(["mock"]);
  });

  it("GET /api/capabilities should return array", async () => {
    const res = await fetch(`${baseUrl}/api/capabilities`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  it("GET /api/memories should return array", async () => {
    const res = await fetch(`${baseUrl}/api/memories`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  it("POST /api/mode should switch mode", async () => {
    const res = await fetch(`${baseUrl}/api/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "kid" }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.mode).toBe("kid");

    // Verify state changed
    expect(stateService.getMode()).toBe("kid");

    // Reset
    stateService.setMode("normal");
  });

  it("POST /api/mode should reject invalid mode", async () => {
    const res = await fetch(`${baseUrl}/api/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "invalid" }),
    });
    expect(res.status).toBe(400);
  });

  it("POST /api/stop should trigger emergency stop", async () => {
    const res = await fetch(`${baseUrl}/api/stop`, { method: "POST" });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  it("POST /api/invoke should return error for unknown capability", async () => {
    const res = await fetch(`${baseUrl}/api/invoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ capability_id: "tool.nonexistent", params: {} }),
    });
    const body = await res.json();
    // Either HTTP 500 or success:false in body
    expect(body.success === false || res.status === 500).toBe(true);
  });

  it("POST /api/invoke should require capability_id", async () => {
    const res = await fetch(`${baseUrl}/api/invoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
  });

  it("GET /api/audit should return array", async () => {
    const res = await fetch(`${baseUrl}/api/audit`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  it("POST /api/chat should require text", async () => {
    const res = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
  });

  // ─── Memory management endpoints ──────────────────────────

  it("DELETE /api/memories/:id should delete memory", async () => {
    // Create a memory first
    const entry = memoryService.create({
      type: "preference",
      content: { key: "test" },
      summary: "Test memory for deletion",
      source: "user_explicit",
    });

    const res = await fetch(`${baseUrl}/api/memories/${entry.id}`, {
      method: "DELETE",
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);

    // Verify deleted
    expect(memoryService.getById(entry.id)).toBeNull();
  });

  it("DELETE /api/memories/:id should return 404 for unknown ID", async () => {
    const res = await fetch(`${baseUrl}/api/memories/nonexistent`, {
      method: "DELETE",
    });
    expect(res.status).toBe(404);
  });

  it("POST /api/memories/clear should clear by type", async () => {
    memoryService.create({
      type: "fact",
      content: { key: "clear-test" },
      summary: "Fact to clear",
      source: "user_explicit",
    });

    const res = await fetch(`${baseUrl}/api/memories/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "fact" }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.cleared).toBeGreaterThanOrEqual(1);
  });

  it("POST /api/memories/clear should reject invalid type", async () => {
    const res = await fetch(`${baseUrl}/api/memories/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "badtype" }),
    });
    expect(res.status).toBe(400);
  });

  it("GET /api/memories/export should return export data", async () => {
    const res = await fetch(`${baseUrl}/api/memories/export`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.version).toBe("1.0.0");
    expect(Array.isArray(body.entries)).toBe(true);
  });

  it("GET /api/memories/search should search by keyword", async () => {
    memoryService.create({
      type: "preference",
      content: { key: "search-test" },
      summary: "Unique searchable memory XYZ123",
      source: "user_explicit",
    });

    const res = await fetch(`${baseUrl}/api/memories/search?q=XYZ123`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.length).toBeGreaterThanOrEqual(1);
    expect(body[0].summary).toContain("XYZ123");
  });

  it("GET /api/memories/search should require q parameter", async () => {
    const res = await fetch(`${baseUrl}/api/memories/search`);
    expect(res.status).toBe(400);
  });

  // ─── Module endpoints ──────────────────────────────────────

  it("GET /api/modules should return array", async () => {
    const res = await fetch(`${baseUrl}/api/modules`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  // ─── Skill endpoints ──────────────────────────────────────

  it("GET /api/skills should return array", async () => {
    const res = await fetch(`${baseUrl}/api/skills`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  // ─── Session endpoints ──────────────────────────────────────

  it("GET /api/sessions should return array (no recorder)", async () => {
    const res = await fetch(`${baseUrl}/api/sessions`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  it("GET /api/sessions/:id/replay should return 404 (no recorder)", async () => {
    const res = await fetch(`${baseUrl}/api/sessions/nonexistent/replay`);
    expect(res.status).toBe(404);
  });

  // ─── Watchdog endpoints ──────────────────────────────────

  it("GET /api/watchdog should return array (no watchdog)", async () => {
    const res = await fetch(`${baseUrl}/api/watchdog`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  // ─── Rule engine endpoints ──────────────────────────────

  it("GET /api/rules/status should return status (no engine)", async () => {
    const res = await fetch(`${baseUrl}/api/rules/status`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.available).toBe(false);
  });

  it("POST /api/rules/evaluate should return 404 (no engine)", async () => {
    const res = await fetch(`${baseUrl}/api/rules/evaluate`, { method: "POST" });
    expect(res.status).toBe(404);
  });

  // ─── Metrics endpoint ──────────────────────────────────

  it("GET /api/metrics should return array (no tracker)", async () => {
    const res = await fetch(`${baseUrl}/api/metrics`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });
});
