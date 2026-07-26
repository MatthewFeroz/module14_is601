import { describe, expect, test } from "bun:test";
import "./script.js";

const {
  calculatePreview,
  parseCalculationInputs,
  validateCalculationInputs,
} = globalThis.CalculationUI;

describe("calculation form validation", () => {
  test("parses finite comma-separated numbers", () => {
    expect(parseCalculationInputs("10, -2.5, 4")).toEqual({
      valid: true,
      values: [10, -2.5, 4],
      error: null,
    });
  });

  test("rejects missing and nonnumeric entries instead of filtering them out", () => {
    expect(parseCalculationInputs("10,,4").valid).toBe(false);
    expect(parseCalculationInputs("10, nope, 4").error).toBe(
      "Every input must be a valid number.",
    );
  });

  test("rejects zero divisors", () => {
    expect(validateCalculationInputs("10, 0", "division")).toEqual({
      valid: false,
      values: [],
      error: "Division by zero is not allowed.",
    });
  });
});

describe("calculation preview", () => {
  test("applies sequential operations in input order", () => {
    expect(calculatePreview("subtraction", [20, 5, 3])).toBe(12);
    expect(calculatePreview("division", [100, 2, 5])).toBe(10);
  });
});
