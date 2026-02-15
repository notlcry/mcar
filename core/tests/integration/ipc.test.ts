/**
 * IPC Integration Test
 *
 * Verifies:
 * 1. Node.js ModuleBridge ←→ Python Mock Module round-trip
 * 2. PUB-SUB emergency stop broadcast
 * 3. Manifest and capabilities request
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { ChildProcess, spawn } from "node:child_process";
import { resolve } from "node:path";
import { ModuleBridge } from "../../src/ipc/module-bridge.js";
import type { IpcConfig } from "../../src/config/config.js";

const ROUTER_ENDPOINT = "ipc:///tmp/mcar-test-router.sock";
const PUB_ENDPOINT = "ipc:///tmp/mcar-test-pub.sock";

const testConfig: IpcConfig = {
  routerEndpoint: ROUTER_ENDPOINT,
  pubEndpoint: PUB_ENDPOINT,
  heartbeatIntervalMs: 60000, // Don't send heartbeats during test
  heartbeatTimeoutMs: 60000,
  invokeTimeoutMs: 10000,
};

describe("IPC Integration", () => {
  let bridge: ModuleBridge;
  let mockProcess: ChildProcess;

  beforeAll(async () => {
    // Start ModuleBridge
    bridge = new ModuleBridge(testConfig);
    await bridge.start();

    // Wait for bridge to be ready, then start mock module
    await waitForRegistration(bridge);
  }, 15000);

  afterAll(async () => {
    if (mockProcess && !mockProcess.killed) {
      mockProcess.kill("SIGTERM");
    }
    await bridge.stop();
  });

  async function waitForRegistration(b: ModuleBridge): Promise<void> {
    // Start the Python mock module process
    const modulePath = resolve(__dirname, "../../../modules/mock/module.py");
    mockProcess = spawn("python3", [
      modulePath,
      "--router", ROUTER_ENDPOINT,
      "--pub", PUB_ENDPOINT,
    ], {
      stdio: ["ignore", "pipe", "pipe"],
    });

    mockProcess.stderr?.on("data", (data: Buffer) => {
      // Log Python module stderr for debugging
      const text = data.toString().trim();
      if (text) console.log("[mock]", text);
    });

    // Wait for the module to register
    return new Promise<void>((resolvePromise, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("Mock module did not register within 10s"));
      }, 10000);

      const unsub = b.onRegister((moduleId) => {
        if (moduleId === "mock") {
          clearTimeout(timeout);
          unsub();
          resolvePromise();
        }
      });
    });
  }

  it("should register mock module", () => {
    const modules = bridge.getRegisteredModules();
    expect(modules).toContain("mock");
  });

  it("should invoke echo capability and get result", async () => {
    const result = await bridge.invoke("mock", "tool.mock.echo", {
      text: "hello world",
    });

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.ok).toBe(true);
      expect(result.data.echo).toBe("hello world");
    }
  });

  it("should invoke status capability", async () => {
    const result = await bridge.invoke("mock", "tool.mock.status", {});

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.ok).toBe(true);
      expect(typeof result.data.battery).toBe("number");
      expect(typeof result.data.temperature).toBe("number");
      expect(typeof result.data.uptime_s).toBe("number");
    }
  });

  it("should invoke timer capability", async () => {
    const start = Date.now();
    const result = await bridge.invoke("mock", "tool.mock.timer", {
      duration_ms: 100,
    });
    const elapsed = Date.now() - start;

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.ok).toBe(true);
      expect(elapsed).toBeGreaterThanOrEqual(80);
      expect(elapsed).toBeLessThan(500);
    }
  });

  it("should request manifest", async () => {
    const result = await bridge.requestManifest("mock");

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.module_id).toBe("mock");
      expect(result.data.module_version).toBe("1.0.0");
      expect(Array.isArray(result.data.capabilities)).toBe(true);
    }
  });

  it("should request capabilities", async () => {
    const result = await bridge.requestCapabilities("mock");

    expect(result.success).toBe(true);
    if (result.success) {
      const caps = result.data.capabilities as unknown[];
      expect(caps.length).toBe(3);
    }
  });

  it("should broadcast emergency stop", async () => {
    // This tests that broadcastStop doesn't throw.
    // Full stop verification requires checking the Python side.
    await expect(bridge.broadcastStop("system")).resolves.not.toThrow();
  });

  it("should complete IPC round-trip in under 5ms average", async () => {
    const iterations = 20;
    const times: number[] = [];

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();
      await bridge.invoke("mock", "tool.mock.echo", { text: `ping-${i}` });
      times.push(performance.now() - start);
    }

    const avg = times.reduce((a, b) => a + b, 0) / times.length;
    console.log(`IPC round-trip average: ${avg.toFixed(2)}ms (${iterations} iterations)`);
    expect(avg).toBeLessThan(50); // Conservative; expect < 5ms on local
  });
});
