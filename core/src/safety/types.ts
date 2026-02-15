/**
 * Safety Policy Engine types.
 */

export type PolicyDecision =
  | { readonly allowed: true }
  | {
      readonly allowed: false;
      readonly code: string;
      readonly reason: string;
      readonly userMessage?: string;
      readonly retryable: boolean;
      readonly retryAfterMs?: number;
    }
  | {
      readonly allowed: "confirm";
      readonly reason: string;
      readonly confirmHint?: string;
    };

export interface SafetyState {
  safetyLock: boolean;
  safetyLockExpiresAt: number;
}
