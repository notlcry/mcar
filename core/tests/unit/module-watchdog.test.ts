/**
 * ModuleWatchdog tests.
 *
 * Tests the watchdog logic using a real temp directory with a fake module script.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { resolve, join } from "node:path";
import { tmpdir } from "node:os";
import { ModuleWatchdog } from "../../src/health/module-watchdog.js";
import { AuditLogger } from "../../src/audit/audit-logger.js";
import { IncidentRecorder } from "../../src/observability/incident-recorder.js";
import { MemoryService } from "../../src/memory/memory-service.js";

const IPC_CONFIG = {
  routerEndpoint: "ipc:///tmp/mcar-test-router.sock",
  pubEndpoint: "ipc:///tmp/mcar-test-pub.sock",
  heartbeatIntervalMs: 5000,
  heartbeatTimeoutMs: 15000,
  invokeTimeoutMs: 10000,
};

describe("ModuleWatchdog", () => {
  let tempDir: string;
  let auditLogger: AuditLogger;
  let watchdog: ModuleWatchdog;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), "mcar-watchdog-"));
    auditLogger = new AuditLogger();
  });

  afterEach(async () => {
    if (watchdog) {
      await watchdog.shutdown();
    }
    rmSync(tempDir, { recursive: true, force: true });
  });

  function createFakeModule(name: string, script: string): void {
    const moduleDir = resolve(tempDir, name);
    mkdirSync(moduleDir, { recursive: true });
    writeFileSync(resolve(moduleDir, "module.py"), script);
  }

  it("should return false for non-existent module", () => {
    watchdog = new ModuleWatchdog(tempDir, IPC_CONFIG, auditLogger);
    expect(watchdog.startModule("nonexistent")).toBe(false);
  });

  it("should start a module that exits immediately", async () => {
    createFakeModule("fast_exit", "import sys; sys.exit(0)");

    watchdog = new ModuleWatchdog(tempDir, IPC_CONFIG, auditLogger, {
      maxRestarts: 2,
      baseDelayMs: 100,
    });

    const started = watchdog.startModule("fast_exit");
    expect(started).toBe(true);

    const status = watchdog.getStatus();
    expect(status).toHaveLength(1);
    expect(status[0].name).toBe("fast_exit");
  });

  it("should start multiple modules", () => {
    createFakeModule("mod_a", "import time; time.sleep(60)");
    createFakeModule("mod_b", "import time; time.sleep(60)");

    watchdog = new ModuleWatchdog(tempDir, IPC_CONFIG, auditLogger);
    const started = watchdog.startModules(["mod_a", "mod_b", "nonexistent"]);

    expect(started).toEqual(["mod_a", "mod_b"]);
    expect(watchdog.getStatus()).toHaveLength(2);
    expect(watchdog.getProcesses()).toHaveLength(2);
  });

  it("should mark module as permanently failed after max restarts", async () => {
    createFakeModule("crasher", "import sys; sys.exit(1)");

    watchdog = new ModuleWatchdog(tempDir, IPC_CONFIG, auditLogger, {
      maxRestarts: 2,
      baseDelayMs: 50,
      maxDelayMs: 100,
    });

    watchdog.startModule("crasher");

    // Wait for restarts to exhaust
    await new Promise((r) => setTimeout(r, 1000));

    const status = watchdog.getStatus();
    const crasher = status.find((s) => s.name === "crasher");
    expect(crasher?.permanentlyFailed).toBe(true);
    expect(crasher?.restartCount).toBe(2);

    // Check audit events
    const events = auditLogger.getRecent(20);
    const failedEvent = events.find(
      (e) => e.eventType === "module.permanently_failed"
    );
    expect(failedEvent).toBeTruthy();
    expect(failedEvent?.payload?.module).toBe("crasher");
  });

  it("should shutdown all modules gracefully", async () => {
    createFakeModule("sleeper", "import time; time.sleep(60)");

    watchdog = new ModuleWatchdog(tempDir, IPC_CONFIG, auditLogger);
    watchdog.startModule("sleeper");

    // Small delay for process to start
    await new Promise((r) => setTimeout(r, 200));

    const processes = watchdog.getProcesses();
    expect(processes.length).toBe(1);

    await watchdog.shutdown();

    const status = watchdog.getStatus();
    expect(status[0].running).toBe(false);
  });

  it("should log restart events to audit logger", async () => {
    createFakeModule("flaky", "import sys; sys.exit(1)");

    watchdog = new ModuleWatchdog(tempDir, IPC_CONFIG, auditLogger, {
      maxRestarts: 1,
      baseDelayMs: 50,
    });

    watchdog.startModule("flaky");

    // Wait for exit + restart cycle
    await new Promise((r) => setTimeout(r, 500));

    const events = auditLogger.getRecent(20);
    const exitEvents = events.filter((e) => e.eventType === "module.exit");
    expect(exitEvents.length).toBeGreaterThanOrEqual(1);

    const restartEvents = events.filter((e) => e.eventType === "module.restarting");
    expect(restartEvents.length).toBeGreaterThanOrEqual(1);
  });

  it("should record incident when module permanently fails", async () => {
    createFakeModule("incident_crasher", "import sys; sys.exit(1)");

    const memoryService = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
    const incidentRecorder = new IncidentRecorder(memoryService, auditLogger);

    watchdog = new ModuleWatchdog(tempDir, IPC_CONFIG, auditLogger, {
      maxRestarts: 1,
      baseDelayMs: 50,
      maxDelayMs: 100,
    });
    watchdog.setIncidentRecorder(incidentRecorder);

    watchdog.startModule("incident_crasher");

    // Wait for restarts to exhaust
    await new Promise((r) => setTimeout(r, 1000));

    const status = watchdog.getStatus();
    const crashed = status.find((s) => s.name === "incident_crasher");
    expect(crashed?.permanentlyFailed).toBe(true);

    // Verify incident memory was created
    const memories = memoryService.search({ types: ["incident"] });
    const permanent = memories.find(
      (m) => m.content.error_code === "PERMANENTLY_FAILED" && m.content.module_id === "incident_crasher"
    );
    expect(permanent).toBeTruthy();
    expect(permanent!.source).toBe("system_detected");

    memoryService.close();
  });
});
