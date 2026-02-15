/**
 * HealthMonitor — periodic module health checks and system status reporting.
 *
 * Polls module health endpoints at a configurable interval,
 * updates StateService with aggregated health data,
 * and logs anomalies to AuditLogger.
 */

import type { CapabilityRegistry } from "../capability/registry.js";
import type { ModuleBridge } from "../ipc/module-bridge.js";
import type { StateService } from "../state/state-service.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import { ModuleProxy } from "../ipc/module-proxy.js";

export interface ModuleHealth {
  readonly moduleId: string;
  readonly status: "healthy" | "degraded" | "offline";
  readonly lastCheck: string;
  readonly details?: Record<string, unknown>;
}

export interface SystemHealth {
  readonly overall: "healthy" | "degraded" | "offline";
  readonly modules: readonly ModuleHealth[];
  readonly uptime_ms: number;
  readonly timestamp: string;
}

export class HealthMonitor {
  private timer: ReturnType<typeof setInterval> | null = null;
  private moduleHealthMap = new Map<string, ModuleHealth>();
  private readonly startTime = Date.now();

  constructor(
    private readonly registry: CapabilityRegistry,
    private readonly bridge: ModuleBridge,
    private readonly stateService: StateService,
    private readonly auditLogger: AuditLogger,
    private readonly intervalMs: number = 30_000
  ) {}

  /**
   * Start periodic health checks.
   */
  start(): void {
    if (this.timer) return;
    this.checkAll(); // Immediate first check
    this.timer = setInterval(() => this.checkAll(), this.intervalMs);
  }

  /**
   * Stop periodic health checks.
   */
  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  /**
   * Run health checks on all registered modules.
   */
  async checkAll(): Promise<void> {
    const modules = this.registry.listModules();

    for (const mod of modules) {
      if (!mod.enabled) {
        this.moduleHealthMap.set(mod.manifest.module_id, {
          moduleId: mod.manifest.module_id,
          status: "offline",
          lastCheck: new Date().toISOString(),
          details: { reason: "disabled" },
        });
        continue;
      }

      await this.checkModule(mod.manifest.module_id);
    }
  }

  /**
   * Check a single module's health.
   */
  async checkModule(moduleId: string): Promise<ModuleHealth> {
    const proxy = new ModuleProxy(moduleId, this.bridge);
    const now = new Date().toISOString();

    try {
      const result = await proxy.health();
      const health: ModuleHealth = {
        moduleId,
        status: "healthy",
        lastCheck: now,
        details: result as Record<string, unknown>,
      };
      this.moduleHealthMap.set(moduleId, health);
      return health;
    } catch {
      const prev = this.moduleHealthMap.get(moduleId);
      const wasHealthy = !prev || prev.status === "healthy";

      const health: ModuleHealth = {
        moduleId,
        status: "offline",
        lastCheck: now,
        details: { error: "Health check failed" },
      };
      this.moduleHealthMap.set(moduleId, health);

      // Log state change
      if (wasHealthy) {
        this.auditLogger.warn("health", "module.health.degraded", { moduleId });
      }

      return health;
    }
  }

  /**
   * Get current system health snapshot.
   */
  getSystemHealth(): SystemHealth {
    const modules = [...this.moduleHealthMap.values()];
    const hasOffline = modules.some((m) => m.status === "offline");
    const hasDegraded = modules.some((m) => m.status === "degraded");
    const allOffline = modules.length > 0 && modules.every((m) => m.status === "offline");

    let overall: "healthy" | "degraded" | "offline";
    if (allOffline) overall = "offline";
    else if (hasOffline || hasDegraded) overall = "degraded";
    else overall = "healthy";

    return {
      overall,
      modules,
      uptime_ms: Date.now() - this.startTime,
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Get health for a specific module.
   */
  getModuleHealth(moduleId: string): ModuleHealth | undefined {
    return this.moduleHealthMap.get(moduleId);
  }
}
