/**
 * Memory types — per Spec.md Memory Spec.
 */

export type MemoryType =
  | "preference"
  | "fact"
  | "rule"
  | "device"
  | "location"
  | "task"
  | "incident"
  | "skill_state"
  | "other";

export type MemorySource =
  | "user_explicit"
  | "user_implicit"
  | "system_detected"
  | "imported";

export type PrivacyLevel = "private" | "normal" | "shareable";

export interface MemoryEntry {
  readonly id: string;
  readonly type: MemoryType;
  readonly content: Record<string, unknown>;
  readonly summary: string;
  readonly source: MemorySource;
  readonly confidence: number;
  readonly privacy_level: PrivacyLevel;
  readonly tags: readonly string[];
  readonly links: Record<string, string>;
  readonly ttl?: number;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface MemoryCreateInput {
  readonly type: MemoryType;
  readonly content: Record<string, unknown>;
  readonly summary: string;
  readonly source: MemorySource;
  readonly confidence?: number;
  readonly privacy_level?: PrivacyLevel;
  readonly tags?: readonly string[];
  readonly links?: Record<string, string>;
  readonly ttl?: number;
}

export interface MemorySearchOptions {
  readonly types?: readonly MemoryType[];
  readonly tags?: readonly string[];
  readonly keywords?: string;
  readonly limit?: number;
  readonly includePrivate?: boolean;
}
