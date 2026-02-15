/**
 * PerformanceTracker — records operation latencies and computes percentile metrics.
 *
 * Features:
 * - startTimer(operation) → returns finish callback
 * - record(operation, duration_ms) — direct recording
 * - getMetrics(operation) → { count, avg_ms, p50_ms, p95_ms, p99_ms, min_ms, max_ms }
 * - getAllMetrics() → all operations
 * - maxEntries per operation to prevent memory bloat (default: 1000)
 */

export interface OperationMetrics {
  readonly operation: string;
  readonly count: number;
  readonly avg_ms: number;
  readonly p50_ms: number;
  readonly p95_ms: number;
  readonly p99_ms: number;
  readonly min_ms: number;
  readonly max_ms: number;
}

export class PerformanceTracker {
  private readonly entries = new Map<string, number[]>();
  private readonly maxEntries: number;

  constructor(options?: { maxEntries?: number }) {
    this.maxEntries = options?.maxEntries ?? 1000;
  }

  /**
   * Start a timer for an operation. Returns a finish function that records the duration.
   */
  startTimer(operation: string): () => number {
    const start = Date.now();
    return () => {
      const duration = Date.now() - start;
      this.record(operation, duration);
      return duration;
    };
  }

  /**
   * Directly record a duration for an operation.
   */
  record(operation: string, durationMs: number): void {
    let list = this.entries.get(operation);
    if (!list) {
      list = [];
      this.entries.set(operation, list);
    }
    list.push(durationMs);
    if (list.length > this.maxEntries) {
      list.shift();
    }
  }

  /**
   * Get metrics for a specific operation.
   */
  getMetrics(operation: string): OperationMetrics | null {
    const list = this.entries.get(operation);
    if (!list || list.length === 0) return null;
    return this.computeMetrics(operation, list);
  }

  /**
   * Get metrics for all tracked operations.
   */
  getAllMetrics(): OperationMetrics[] {
    const result: OperationMetrics[] = [];
    for (const [operation, list] of this.entries) {
      if (list.length > 0) {
        result.push(this.computeMetrics(operation, list));
      }
    }
    return result;
  }

  /**
   * Reset all recorded data.
   */
  reset(): void {
    this.entries.clear();
  }

  /**
   * Reset data for a specific operation.
   */
  resetOperation(operation: string): void {
    this.entries.delete(operation);
  }

  private computeMetrics(operation: string, values: number[]): OperationMetrics {
    const sorted = [...values].sort((a, b) => a - b);
    const count = sorted.length;
    const sum = sorted.reduce((a, b) => a + b, 0);

    return {
      operation,
      count,
      avg_ms: Math.round(sum / count),
      p50_ms: this.percentile(sorted, 50),
      p95_ms: this.percentile(sorted, 95),
      p99_ms: this.percentile(sorted, 99),
      min_ms: sorted[0],
      max_ms: sorted[count - 1],
    };
  }

  private percentile(sorted: number[], p: number): number {
    if (sorted.length === 1) return sorted[0];
    const idx = (p / 100) * (sorted.length - 1);
    const lower = Math.floor(idx);
    const upper = Math.ceil(idx);
    if (lower === upper) return sorted[lower];
    const fraction = idx - lower;
    return Math.round(sorted[lower] + fraction * (sorted[upper] - sorted[lower]));
  }
}
