/**
 * ContextBuilder — assembles context for each agent invocation.
 *
 * Gathers:
 * - Memory injections (max 5, per Spec.md)
 * - State snapshot
 * - Capability summaries
 * - Module health status (if watchdog provided)
 */

import type { MemoryService } from "../memory/memory-service.js";
import type { StateService } from "../state/state-service.js";
import type { CapabilityRegistry } from "../capability/registry.js";
import type { ModuleWatchdog } from "../health/module-watchdog.js";

export interface SessionContext {
  readonly memories: readonly string[];
  readonly stateSnapshot: Record<string, unknown>;
  readonly capabilities: readonly string[];
  readonly moduleHealth?: readonly string[];
}

export class ContextBuilder {
  private watchdog?: ModuleWatchdog;

  constructor(
    private readonly memoryService: MemoryService,
    private readonly stateService: StateService,
    private readonly registry: CapabilityRegistry,
    watchdog?: ModuleWatchdog
  ) {
    this.watchdog = watchdog;
  }

  setWatchdog(watchdog: ModuleWatchdog): void {
    this.watchdog = watchdog;
  }

  build(): SessionContext {
    const memories = this.memoryService.getInjectionContext();
    const snapshot = this.stateService.getSnapshot();
    const capabilities = this.registry.getCapabilitySummaries().map(
      (c) => `${c.name} (${c.capability_id}) [${c.risk_level}]`
    );

    const context: SessionContext = {
      memories,
      stateSnapshot: snapshot as unknown as Record<string, unknown>,
      capabilities,
    };

    if (this.watchdog) {
      const statuses = this.watchdog.getStatus();
      const health = statuses.map((s) => {
        if (s.permanentlyFailed) return `${s.name}: FAILED`;
        if (!s.running) return `${s.name}: DOWN (restarts: ${s.restartCount})`;
        return `${s.name}: OK`;
      });
      return { ...context, moduleHealth: health };
    }

    return context;
  }
}
