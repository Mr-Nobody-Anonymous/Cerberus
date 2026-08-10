import { describe, it, expect, vi, beforeEach } from "vitest";
import type { DiscoveredEndpoint } from "../src/types/index.js";

// Mock undici's request before importing the module under test.
const mockRequest = vi.fn();

vi.mock("undici", () => ({
  request: (...args: unknown[]) => mockRequest(...args),
}));

const { testIdor } = await import("../src/crawl/api-fuzzer.js");

function makeEndpoint(overrides?: Partial<DiscoveredEndpoint>): DiscoveredEndpoint {
  return {
    url: "https://example.com/api/users/123",
    method: "GET",
    parameters: [],
    ...overrides,
  };
}

function mockBody(text: string) {
  return { text: () => Promise.resolve(text) };
}

// Extract the Authorization / Cookie header from the options object undici
// receives as its 2nd argument. This is how the mock tells identities apart.
function authOf(opts: unknown): string | undefined {
  const headers = (opts as { headers?: Record<string, string> } | undefined)?.headers;
  return headers?.Authorization ?? headers?.Cookie;
}

describe("testIdor (auth-aware)", () => {
  beforeEach(() => {
    mockRequest.mockReset();
  });

  it("two-identity: CONFIRMS high-severity IDOR when identity B reads identity A's resource", async () => {
    // Same resource URL /123. Identity A (Bearer A) and identity B (Bearer B)
    // both get 200 with a similar body → B can read A's data → confirmed IDOR.
    mockRequest.mockImplementation((url: unknown, opts: unknown) => {
      const auth = authOf(opts);
      if (String(url).includes("/123") && (auth === "Bearer A" || auth === "Bearer B")) {
        return Promise.resolve({ statusCode: 200, body: mockBody("A".repeat(120)) });
      }
      return Promise.resolve({ statusCode: 404, body: mockBody("") });
    });

    const findings = await testIdor(makeEndpoint(), { bearerToken: "A", bearerTokenB: "B" }, false);

    expect(findings.length).toBe(1);
    expect(findings[0]!.ruleId).toBe("fuzzer-idor");
    expect(findings[0]!.severity).toBe("high");
    expect(findings[0]!.metadata?.unconfirmed).toBeFalsy();
    expect(findings[0]!.metadata?.identityAStatus).toBe(200);
    expect(findings[0]!.metadata?.identityBStatus).toBe(200);
  });

  it("two-identity: NO finding when identity B is denied (403)", async () => {
    mockRequest.mockImplementation((url: unknown, opts: unknown) => {
      const auth = authOf(opts);
      if (String(url).includes("/123") && auth === "Bearer A") {
        return Promise.resolve({ statusCode: 200, body: mockBody("A".repeat(120)) });
      }
      if (String(url).includes("/123") && auth === "Bearer B") {
        return Promise.resolve({ statusCode: 403, body: mockBody("forbidden") });
      }
      return Promise.resolve({ statusCode: 404, body: mockBody("") });
    });

    const findings = await testIdor(makeEndpoint(), { bearerToken: "A", bearerTokenB: "B" }, false);
    expect(findings.length).toBe(0);
  });

  it("no-auth: SKIPS entirely (unauthenticated ID-diffing is pure noise)", async () => {
    // Even if every request would return distinct 200 content, no auth means
    // no authorization signal → no finding, and ideally no requests at all.
    mockRequest.mockResolvedValue({ statusCode: 200, body: mockBody("distinct body ".repeat(20)) });

    const findings = await testIdor(makeEndpoint(), undefined, false);
    expect(findings.length).toBe(0);
    expect(mockRequest).not.toHaveBeenCalled();
  });

  it("single-identity: MEDIUM finding when an authenticated user reads another record", async () => {
    // Only a single token. Original /123 returns bodyX; sequential /124 returns
    // a distinct, substantive body → likely IDOR (medium, unconfirmed=true —
    // heuristic self-describes as "verify with --auth-bearer-b").
    mockRequest.mockImplementation((url: unknown, opts: unknown) => {
      const auth = authOf(opts);
      if (auth !== "Bearer A") return Promise.resolve({ statusCode: 401, body: mockBody("") });
      if (String(url).includes("/123")) {
        return Promise.resolve({ statusCode: 200, body: mockBody("X".repeat(100)) });
      }
      if (String(url).includes("/124")) {
        return Promise.resolve({ statusCode: 200, body: mockBody("Y".repeat(100)) });
      }
      return Promise.resolve({ statusCode: 404, body: mockBody("") });
    });

    const findings = await testIdor(makeEndpoint(), { bearerToken: "A" }, false);

    expect(findings.length).toBe(1);
    expect(findings[0]!.ruleId).toBe("fuzzer-idor");
    expect(findings[0]!.severity).toBe("medium");
    expect(findings[0]!.metadata?.unconfirmed).toBe(true);
    expect(findings[0]!.metadata?.originalId).toBe("123");
    expect(findings[0]!.metadata?.testId).toBe("124");
  });
});
