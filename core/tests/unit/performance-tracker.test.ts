/**
 * PerformanceTracker unit tests.
 */

import { describe, it, expect } from "vitest";
import { PerformanceTracker } from "../../src/observability/performance-tracker.js";

describe("PerformanceTracker", () => {
  it("should record and return metrics via startTimer", () => {
    const tracker = new PerformanceTracker();
    const finish = tracker.startTimer("op.test");

    // Simulate some work
    const start = Date.now();
    while (Date.now() - start < 10) { /* busy wait */ }

    const duration = finish();
    expect(duration).toBeGreaterThanOrEqual(5);

    const metrics = tracker.getMetrics("op.test");
    expect(metrics).not.toBeNull();
    expect(metrics!.count).toBe(1);
    expect(metrics!.min_ms).toBeGreaterThanOrEqual(5);
  });

  it("should record via record() method", () => {
    const tracker = new PerformanceTracker();
    tracker.record("op.direct", 100);
    tracker.record("op.direct", 200);
    tracker.record("op.direct", 300);

    const metrics = tracker.getMetrics("op.direct");
    expect(metrics).not.toBeNull();
    expect(metrics!.count).toBe(3);
    expect(metrics!.avg_ms).toBe(200);
    expect(metrics!.min_ms).toBe(100);
    expect(metrics!.max_ms).toBe(300);
  });

  it("should compute correct percentiles", () => {
    const tracker = new PerformanceTracker();
    // Record 100 values: 1, 2, 3, ..., 100
    for (let i = 1; i <= 100; i++) {
      tracker.record("op.p", i);
    }

    const metrics = tracker.getMetrics("op.p")!;
    expect(metrics.count).toBe(100);
    // Percentiles use linear interpolation: idx = (p/100) * (n-1)
    // p50: idx = 49.5 → avg(50, 51) = 51 (rounded)
    expect(metrics.p50_ms).toBeGreaterThanOrEqual(50);
    expect(metrics.p50_ms).toBeLessThanOrEqual(51);
    expect(metrics.p95_ms).toBeGreaterThanOrEqual(95);
    expect(metrics.p95_ms).toBeLessThanOrEqual(96);
    expect(metrics.p99_ms).toBeGreaterThanOrEqual(99);
    expect(metrics.p99_ms).toBeLessThanOrEqual(100);
    expect(metrics.min_ms).toBe(1);
    expect(metrics.max_ms).toBe(100);
  });

  it("should enforce maxEntries limit", () => {
    const tracker = new PerformanceTracker({ maxEntries: 5 });
    for (let i = 1; i <= 10; i++) {
      tracker.record("op.limit", i);
    }

    const metrics = tracker.getMetrics("op.limit")!;
    expect(metrics.count).toBe(5);
    // Should keep last 5 values: 6, 7, 8, 9, 10
    expect(metrics.min_ms).toBe(6);
    expect(metrics.max_ms).toBe(10);
  });

  it("should reset all metrics", () => {
    const tracker = new PerformanceTracker();
    tracker.record("op.a", 10);
    tracker.record("op.b", 20);

    tracker.reset();

    expect(tracker.getMetrics("op.a")).toBeNull();
    expect(tracker.getMetrics("op.b")).toBeNull();
    expect(tracker.getAllMetrics()).toHaveLength(0);
  });

  it("should track multiple operations independently", () => {
    const tracker = new PerformanceTracker();
    tracker.record("op.x", 50);
    tracker.record("op.y", 100);
    tracker.record("op.y", 200);

    const all = tracker.getAllMetrics();
    expect(all).toHaveLength(2);

    const x = tracker.getMetrics("op.x")!;
    expect(x.count).toBe(1);
    expect(x.avg_ms).toBe(50);

    const y = tracker.getMetrics("op.y")!;
    expect(y.count).toBe(2);
    expect(y.avg_ms).toBe(150);
  });

  it("should return null for unrecorded operation", () => {
    const tracker = new PerformanceTracker();
    expect(tracker.getMetrics("nonexistent")).toBeNull();
  });

  it("should handle single value percentiles", () => {
    const tracker = new PerformanceTracker();
    tracker.record("op.single", 42);

    const metrics = tracker.getMetrics("op.single")!;
    expect(metrics.p50_ms).toBe(42);
    expect(metrics.p95_ms).toBe(42);
    expect(metrics.p99_ms).toBe(42);
  });
});
