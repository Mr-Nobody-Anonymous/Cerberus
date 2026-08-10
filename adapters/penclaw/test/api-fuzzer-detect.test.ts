import { describe, it, expect } from "vitest";
import { isErrorResponse, looksLikeSsrf } from "../src/crawl/api-fuzzer.js";

describe("isErrorResponse", () => {
  it("does not flag benign mentions of database names", () => {
    expect(isErrorResponse("Our docs cover mysql and postgres setup.", "sql-injection")).toBe(false);
  });
  it("flags a real SQL error", () => {
    expect(isErrorResponse("You have an error in your SQL syntax near '''", "sql-injection")).toBe(true);
  });
  it("does not flag paths merely containing bin/", () => {
    expect(isErrorResponse("GET /usr/local/bin/thing served from cabin/", "command-injection")).toBe(false);
  });
  it("flags a real /etc/passwd leak", () => {
    expect(isErrorResponse("root:x:0:0:root:/root:/bin/bash", "path-traversal")).toBe(true);
  });
});

describe("looksLikeSsrf", () => {
  it("does not flag a normal JSON hostname field", () => {
    expect(looksLikeSsrf('{"hostname":"web-01"}')).toBe(false);
  });
  it("flags AWS metadata markers", () => {
    expect(looksLikeSsrf("iam/security-credentials/role")).toBe(true);
    expect(looksLikeSsrf("ami-id: ami-1234")).toBe(true);
  });
});
