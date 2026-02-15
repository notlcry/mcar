/**
 * ModuleWatchdog — monitors Python module processes and auto-restarts on crash.
 *
 * Features:
 * - Detects module process exit and auto-restarts with exponential backoff
 * - Marks modules as permanently failed after max restart attempts
 * - Logs all lifecycle events to AuditLogger
 * - Provides shutdown method for clean teardown
 */

import { ChildProcess, spawn } from "node:child_process";
import { resolve } from "node:path";
import { existsSync } from "node:fs";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { IpcConfig } from "../config/config.js";
import type { IncidentRecorder } from "../observability/incident-recorder.js";

export interface WatchdogConfig {
  /** Maximum restart attempts before marking as permanently failed. Default: 5 */
  readonly maxRestarts?: number;
  /** Initial delay before restart in ms. Default: 1000 */
  readonly baseDelayMs?: number;
  /** Maximum delay between restarts in ms. Default: 30000 */
  readonly maxDelayMs?: number;
}

interface ManagedModule {
  readonly name: string;
  readonly modulePath: string;
  process: ChildProcess | null;
  restartCount: number;
  permanentlyFailed: boolean;
  stopping: boolean;
}

export class ModuleWatchdog {
  private readonly modules = new Map<string, ManagedModule>();
  private readonly maxRestarts: number;
  private readonly baseDelayMs: number;
  private readonly maxDelayMs: number;
  private shuttingDown = false;

  private incidentRecorder: IncidentRecorder | null = null;

  constructor(
    private readonly modulesDir: string,
    private readonly ipcConfig: IpcConfig,
    private readonly auditLogger: AuditLogger,
    config?: WatchdogConfig
  ) {
    this.maxRestarts = config?.maxRestarts ?? 5;
    this.baseDelayMs = config?.baseDelayMs ?? 1000;
    this.maxDelayMs = config?.maxDelayMs ?? 30000;
  }

  setIncidentRecorder(recorder: IncidentRecorder): void {
    this.incidentRecorder = recorder;
  }

  /**
   * Start a named module process. Returns true if the module was found and started.
   */
  startModule(name: string): boolean {
    const modulePath = resolve(this.modulesDir, name, "module.py");
    if (!existsSync(modulePath)) {
      return false;
    }

    const managed: ManagedModule = {
      name,
      modulePath,
      process: null,
      restartCount: 0,
      permanentlyFailed: false,
      stopping: false,
    };
    this.modules.set(name, managed);
    this.spawnProcess(managed);
    return true;
  }

  /**
   * Start multiple modules at once. Returns list of successfully started module names.
   */
  startModules(names: string[]): string[] {
    const started: string[] = [];
    for (const name of names) {
      if (this.startModule(name)) {
        started.push(name);
      }
    }
    return started;
  }

  /**
   * Get status of all managed modules.
   */
  getStatus(): Array<{
    name: string;
    running: boolean;
    restartCount: number;
    permanentlyFailed: boolean;
    pid?: number;
  }> {
    return [...this.modules.values()].map((m) => ({
      name: m.name,
      running: m.process !== null && !m.process.killed,
      restartCount: m.restartCount,
      permanentlyFailed: m.permanentlyFailed,
      pid: m.process?.pid,
    }));
  }

  /**
   * Get list of all managed module processes (for backward compat).
   */
  getProcesses(): ChildProcess[] {
    return [...this.modules.values()]
      .filter((m) => m.process !== null)
      .map((m) => m.process!);
  }

  /**
   * Shut down all module processes gracefully.
   */
  async shutdown(): Promise<void> {
    this.shuttingDown = true;

    const killPromises = [...this.modules.values()].map((managed) => {
      managed.stopping = true;
      return new Promise<void>((resolveKill) => {
        if (!managed.process || managed.process.killed) {
          resolveKill();
          return;
        }
        managed.process.once("exit", () => resolveKill());
        managed.process.kill("SIGTERM");

        // Force kill after 3 seconds
        setTimeout(() => {
          if (managed.process && !managed.process.killed) {
            managed.process.kill("SIGKILL");
          }
          resolveKill();
        }, 3000);
      });
    });

    await Promise.all(killPromises);
  }

  private spawnProcess(managed: ManagedModule): void {
    if (this.shuttingDown || managed.stopping) return;

    const proc = spawn("python3", [
      managed.modulePath,
      "--router", this.ipcConfig.routerEndpoint,
      "--pub", this.ipcConfig.pubEndpoint,
    ], {
      stdio: ["ignore", "pipe", "pipe"],
    });

    managed.process = proc;

    proc.stdout?.on("data", (data: Buffer) => {
      const text = data.toString().trim();
      if (text) console.log(`[${managed.name}] ${text}`);
    });

    proc.stderr?.on("data", (data: Buffer) => {
      const text = data.toString().trim();
      if (text) console.log(`[${managed.name}] ${text}`);
    });

    proc.on("exit", (code, signal) => {
      managed.process = null;

      if (this.shuttingDown || managed.stopping) return;

      this.auditLogger.warn("watchdog", "module.exit", {
        module: managed.name,
        code,
        signal,
        restartCount: managed.restartCount,
      });

      this.incidentRecorder?.record({
        category: "module_crash",
        error_code: `EXIT_${code ?? signal ?? "UNKNOWN"}`,
        message: `Module ${managed.name} exited unexpectedly (code=${code}, signal=${signal})`,
        module_id: managed.name,
        details: { restartCount: managed.restartCount },
      });

      this.scheduleRestart(managed);
    });
  }

  private scheduleRestart(managed: ManagedModule): void {
    if (managed.restartCount >= this.maxRestarts) {
      managed.permanentlyFailed = true;
      this.auditLogger.error("watchdog", "module.permanently_failed", {
        module: managed.name,
        totalRestarts: managed.restartCount,
      });
      this.incidentRecorder?.record({
        category: "module_crash",
        error_code: "PERMANENTLY_FAILED",
        message: `Module ${managed.name} permanently failed after ${managed.restartCount} restarts`,
        module_id: managed.name,
        details: { totalRestarts: managed.restartCount },
      });
      return;
    }

    managed.restartCount++;
    const delay = Math.min(
      this.baseDelayMs * Math.pow(2, managed.restartCount - 1),
      this.maxDelayMs
    );

    this.auditLogger.info("watchdog", "module.restarting", {
      module: managed.name,
      attempt: managed.restartCount,
      delayMs: delay,
    });

    setTimeout(() => {
      if (!this.shuttingDown && !managed.stopping) {
        this.spawnProcess(managed);
      }
    }, delay);
  }
}
