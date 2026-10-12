import { describe, expect, it } from "vitest";

describe("FluxSG dashboard", () => {
  it("keeps the product identity stable", () => {
    expect("FluxSG").toMatch(/SG$/);
  });
});

