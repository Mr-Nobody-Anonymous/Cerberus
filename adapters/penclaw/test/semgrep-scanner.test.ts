import { describe, it, expect } from "vitest";
import { isLocalRulePath } from "../src/scanners/semgrep-scanner.js";

describe("semgrep customRules validation", () => {
  it("rejects URLs and registry refs", () => {
    expect(isLocalRulePath("https://evil.com/rules.yml")).toBe(false);
    expect(isLocalRulePath("http://evil/rules")).toBe(false);
    expect(isLocalRulePath("p/ci")).toBe(false);       // registry shorthand
    expect(isLocalRulePath("r/generic")).toBe(false);  // registry shorthand
  });
  it("accepts local paths", () => {
    expect(isLocalRulePath("./rules/custom.yml")).toBe(true);
    expect(isLocalRulePath("/abs/rules.yml")).toBe(true);
    expect(isLocalRulePath("rules.yaml")).toBe(true);
  });
});
