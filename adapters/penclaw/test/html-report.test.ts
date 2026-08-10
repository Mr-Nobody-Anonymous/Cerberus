import { describe, it, expect } from "vitest";
import { escHtml } from "../src/reporters/html.js";

describe("escHtml", () => {
  it("escapes &, <, >, and \" exactly", () => {
    expect(escHtml('<script>"x"&y')).toBe("&lt;script&gt;&quot;x&quot;&amp;y");
  });

  it("neutralizes tag injection", () => {
    const escaped = escHtml("<img src=x onerror=alert(1)>");
    expect(escaped).not.toContain("<img");
    expect(escaped).not.toContain(">");
    expect(escaped).toContain("&lt;img");
  });

  it("escapes ampersand before other entities (no double-encoding artifacts)", () => {
    expect(escHtml("a & b")).toBe("a &amp; b");
  });
});
