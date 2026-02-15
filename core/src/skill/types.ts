/**
 * Skill types — multi-tool composition definitions.
 *
 * A Skill is a sequence of Steps, each invoking a capability (tool).
 * Steps can have conditions, retries, and error handlers.
 */

export type StepCondition =
  | { readonly type: "state"; readonly key: string; readonly op: "==" | "!=" | ">" | "<"; readonly value: unknown }
  | { readonly type: "previous_result"; readonly path: string; readonly op: "==" | "!=" | "truthy" | "falsy"; readonly value?: unknown };

export interface SkillStep {
  readonly id: string;
  readonly capability_id: string;
  readonly params: Record<string, unknown>;
  /** Dynamic params resolved from previous step results via $ref syntax */
  readonly param_refs?: Record<string, string>;
  readonly condition?: StepCondition;
  readonly on_error?: "skip" | "abort" | "retry";
  readonly max_retries?: number;
  readonly delay_ms?: number;
}

export interface SkillDefinition {
  readonly skill_id: string;
  readonly name: string;
  readonly description: string;
  readonly version: string;
  readonly risk_level: "READ_ONLY" | "NORMAL" | "DANGEROUS";
  readonly parameters?: Record<string, {
    readonly type: string;
    readonly description?: string;
    readonly default?: unknown;
    readonly required?: boolean;
  }>;
  readonly steps: readonly SkillStep[];
}

export interface SkillExecutionResult {
  readonly skill_id: string;
  readonly success: boolean;
  readonly steps_completed: number;
  readonly steps_total: number;
  readonly results: Record<string, unknown>;
  readonly error?: string;
  readonly aborted_at_step?: string;
}
