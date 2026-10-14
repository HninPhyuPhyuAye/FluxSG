import { describe, expect, it } from "vitest";

import { enforceForecastFreshness, psiLevel } from "../lib/api";
import type { ForecastSnapshot } from "../lib/api";

describe("FluxSG dashboard", () => {
  it("keeps the product identity stable", () => {
    expect("FluxSG").toMatch(/SG$/);
  });

  it.each([
    [50, "Good"],
    [51, "Moderate"],
    [100, "Moderate"],
    [101, "Unhealthy"],
    [200, "Unhealthy"],
    [201, "Very Unhealthy"],
    [300, "Very Unhealthy"],
    [301, "Hazardous"],
  ])("classifies PSI %i as %s", (psi, expected) => {
    expect(psiLevel(psi)).toBe(expected);
  });

  it("withholds a forecast after its source observation expires", () => {
    const snapshot: ForecastSnapshot = {
      schema_version: 1,
      forecast_type: "regional 24-hour PSI one hour ahead",
      source: "NEA",
      source_url: "https://example.test/psi",
      generated_at: "2026-10-14T00:00:00Z",
      observed_at: "2026-10-14T00:00:00Z",
      forecast_for: "2026-10-14T01:00:00Z",
      available: true,
      status: "available",
      expires_at: "2026-10-14T01:00:00Z",
      reason: "All release guardrails passed.",
      checks: { source_fresh: true },
      freshness_hours: 0,
      model: {
        name: "test",
        version: "test-v1",
        trained_through: "2026-10-14T00:00:00Z",
        age_hours: 0,
        test_mae: 0.5,
        persistence_mae: 0.6,
        interval_coverage: 0.9,
        backtest_wins: 3,
        backtest_folds: 4,
      },
      drift: { status: "healthy" },
      forecasts: [],
      disclaimer: "Experimental estimate.",
    };

    const guarded = enforceForecastFreshness(snapshot, Date.parse("2026-10-14T01:00:01Z"));

    expect(guarded.available).toBe(false);
    expect(guarded.status).toBe("withheld");
    expect(guarded.checks.source_fresh).toBe(false);
  });

  it("marks an already-withheld forecast stale after expiry", () => {
    const snapshot: ForecastSnapshot = {
      schema_version: 1,
      forecast_type: "regional 24-hour PSI one hour ahead",
      source: "NEA",
      source_url: "https://example.test/psi",
      generated_at: "2026-10-14T00:00:00Z",
      observed_at: "2026-10-14T00:00:00Z",
      forecast_for: "2026-10-14T01:00:00Z",
      available: false,
      status: "withheld",
      expires_at: "2026-10-14T01:00:00Z",
      reason: "Forecast withheld because a model-quality check failed.",
      checks: { source_fresh: true, drift_clear: false },
      freshness_hours: 0,
      model: {
        name: "test",
        version: "test-v1",
        trained_through: "2026-10-14T00:00:00Z",
        age_hours: 0,
        test_mae: 0.7,
        persistence_mae: 0.6,
        interval_coverage: 0.8,
        backtest_wins: 2,
        backtest_folds: 4,
      },
      drift: { status: "alert" },
      forecasts: [],
      disclaimer: "Experimental estimate.",
    };

    const guarded = enforceForecastFreshness(snapshot, Date.parse("2026-10-14T01:00:01Z"));

    expect(guarded.available).toBe(false);
    expect(guarded.status).toBe("withheld");
    expect(guarded.checks.source_fresh).toBe(false);
    expect(guarded.reason).toContain("expired");
  });
});
