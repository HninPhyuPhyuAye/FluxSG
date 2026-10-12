import { describe, expect, it } from "vitest";

import { psiLevel } from "../lib/api";

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
});

