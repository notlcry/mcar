/**
 * RuleEngine — evaluates memory entries of type "rule" and
 * triggers actions when conditions are met.
 *
 * Supported conditions:
 * - time_range: "HH:MM-HH:MM" (e.g., "22:00-07:00")
 * - state: { key, op, value } (checks StateService)
 *
 * Supported actions:
 * - set_mode: { mode: Mode }
 * - invoke: { capability_id, params }
 *
 * Runs periodically (default: every 60s).
 */

import type { MemoryService } from "../memory/memory-service.js";
import type { StateService } from "../state/state-service.js";
import type { CapabilityExecutor } from "../capability/executor.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { Mode } from "../state/types.js";

// ─── Rule content schema ─────────────────────────────────────

export interface RuleCondition {
  readonly time_range?: string;       // "HH:MM-HH:MM"
  readonly state?: {
    readonly key: string;
    readonly op: "==" | "!=" | ">" | ">=" | "<" | "<=";
    readonly value: unknown;
  };
}

export interface RuleAction {
  readonly action: "set_mode" | "invoke";
  readonly mode?: string;             // for set_mode
  readonly capability_id?: string;    // for invoke
  readonly params?: Record<string, unknown>;
}

export interface RuleContent {
  readonly rule_id: string;
  readonly when: RuleCondition;
  readonly then: RuleAction;
}

export interface RuleEngineConfig {
  readonly intervalMs?: number;   // default 60000
}

export class RuleEngine {
  private timer: ReturnType<typeof setInterval> | null = null;
  private readonly intervalMs: number;
  private readonly activeRules = new Set<string>(); // track which rules are currently active

  constructor(
    private readonly memoryService: MemoryService,
    private readonly stateService: StateService,
    private readonly executor: CapabilityExecutor | null,
    private readonly auditLogger: AuditLogger,
    config?: RuleEngineConfig
  ) {
    this.intervalMs = config?.intervalMs ?? 60_000;
  }

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => this.evaluate(), this.intervalMs);
    // Run initial evaluation immediately
    this.evaluate();
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  /**
   * Evaluate all rules and trigger actions.
   * Returns a summary of triggered rules.
   */
  evaluate(): Array<{ ruleId: string; action: string }> {
    const triggered: Array<{ ruleId: string; action: string }> = [];

    const ruleEntries = this.memoryService.search({ types: ["rule"], includePrivate: true, limit: 100 });

    for (const entry of ruleEntries) {
      const content = entry.content as unknown as RuleContent;
      if (!content.rule_id || !content.when || !content.then) continue;

      const conditionMet = this.evaluateCondition(content.when);

      if (conditionMet && !this.activeRules.has(content.rule_id)) {
        // Condition just became true — trigger action
        this.activeRules.add(content.rule_id);
        this.triggerAction(content);
        triggered.push({ ruleId: content.rule_id, action: content.then.action });
      } else if (!conditionMet && this.activeRules.has(content.rule_id)) {
        // Condition no longer met — deactivate
        this.activeRules.delete(content.rule_id);
      }
    }

    return triggered;
  }

  // ─── Condition evaluation ───────────────────────────────────

  evaluateCondition(when: RuleCondition): boolean {
    if (when.time_range) {
      if (!this.evaluateTimeRange(when.time_range)) return false;
    }
    if (when.state) {
      if (!this.evaluateState(when.state)) return false;
    }
    return true;
  }

  private evaluateTimeRange(range: string, now?: Date): boolean {
    const match = range.match(/^(\d{2}):(\d{2})-(\d{2}):(\d{2})$/);
    if (!match) return false;

    const [, startH, startM, endH, endM] = match;
    const current = now ?? new Date();
    const currentMinutes = current.getHours() * 60 + current.getMinutes();
    const startMinutes = parseInt(startH) * 60 + parseInt(startM);
    const endMinutes = parseInt(endH) * 60 + parseInt(endM);

    // Handle overnight ranges (e.g., 22:00-07:00)
    if (startMinutes > endMinutes) {
      return currentMinutes >= startMinutes || currentMinutes < endMinutes;
    }

    return currentMinutes >= startMinutes && currentMinutes < endMinutes;
  }

  private evaluateState(state: { key: string; op: string; value: unknown }): boolean {
    const actual = this.stateService.get(state.key);
    if (actual === undefined) return false;

    switch (state.op) {
      case "==": return actual === state.value;
      case "!=": return actual !== state.value;
      case ">":  return (actual as number) > (state.value as number);
      case ">=": return (actual as number) >= (state.value as number);
      case "<":  return (actual as number) < (state.value as number);
      case "<=": return (actual as number) <= (state.value as number);
      default: return false;
    }
  }

  // ─── Action triggering ──────────────────────────────────────

  private triggerAction(content: RuleContent): void {
    const { then } = content;

    this.auditLogger.info("rule-engine", "rule.triggered", {
      rule_id: content.rule_id,
      action: then.action,
    });

    switch (then.action) {
      case "set_mode":
        if (then.mode) {
          this.stateService.setMode(then.mode as Mode);
          this.auditLogger.info("rule-engine", "rule.set_mode", {
            rule_id: content.rule_id,
            mode: then.mode,
          });
        }
        break;

      case "invoke":
        if (then.capability_id && this.executor) {
          this.executor
            .execute(then.capability_id, then.params ?? {})
            .then((result) => {
              this.auditLogger.info("rule-engine", "rule.invoke.result", {
                rule_id: content.rule_id,
                capability_id: then.capability_id,
                success: result.success,
              });
            })
            .catch((err) => {
              this.auditLogger.error("rule-engine", "rule.invoke.error", {
                rule_id: content.rule_id,
                error: err instanceof Error ? err.message : String(err),
              });
            });
        }
        break;
    }
  }
}
