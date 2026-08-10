import { describe, it, expect, vi, beforeEach } from "vitest";
import type { DiscoveredEndpoint } from "../src/types/index.js";

// We need to mock undici's request before importing the module
const mockRequest = vi.fn();

vi.mock("undici", () => ({
  request: (...args: unknown[]) => mockRequest(...args),
}));

// Import after mocking
const { detectTimeBased, detectBooleanBased } = await import("../src/crawl/api-fuzzer.js");

function makeEndpoint(overrides?: Partial<DiscoveredEndpoint>): DiscoveredEndpoint {
  return {
    url: "https://example.com/api/search?q=test",
    method: "GET",
    parameters: ["q"],
    ...overrides,
  };
}

function mockBody(text: string) {
  return { text: () => Promise.resolve(text) };
}

// A deterministic clock injected as the 2nd arg to detectTimeBased. It returns
// timestamps from a scripted queue; once the queue is exhausted it repeats the
// last value, so any extra now() calls (e.g. remaining non-triggering payloads)
// yield a zero elapsed time. No global Date.now patching is needed.
//
// detectTimeBased calls now() in this exact order:
//   baseline request 1: start, end            (2 calls)
//   baseline request 2: start, end            (2 calls)
//   per time payload:   start, end            (2 calls)
//   on trigger only:    confirm start, end    (2 calls, then break)
function scriptedNow(sequence: number[]): () => number {
  let i = 0;
  let last = sequence.length > 0 ? sequence[0]! : 0;
  return () => {
    if (i < sequence.length) {
      last = sequence[i]!;
      i++;
    }
    return last;
  };
}

describe("detectTimeBased", () => {
  beforeEach(() => {
    mockRequest.mockReset();
  });

  it("detects time-based blind SQLi on a SLOW baseline (delta-based)", async () => {
    mockRequest.mockResolvedValue({ statusCode: 200, body: mockBody("ok") });

    // baseline ≈ 2000ms/req, payload elapsed ≈ 7000ms (delta ≈ 5000),
    // confirmation ≈ 7000ms. delta clears the 3500ms/2000ms thresholds.
    // NOTE: the OLD `elapsed > baseline*5 && > 4000` rule needed >10000ms here
    // (5 * 2000), so it would MISS this real injection — that is the point.
    // now() sequence (absolute ms):
    //   baseline1: 0 -> 2000   (2000ms)
    //   baseline2: 2000 -> 4000 (2000ms)  => baselineMs = 2000
    //   payload:   4000 -> 11000 (7000ms) => delta 5000 -> trigger
    //   confirm:   11000 -> 18000 (7000ms) => delta 5000 -> finding
    const now = scriptedNow([0, 2000, 2000, 4000, 4000, 11000, 11000, 18000]);

    const findings = await detectTimeBased(makeEndpoint(), now);

    expect(findings.length).toBe(1);
    expect(findings[0]!.ruleId).toBe("fuzzer-blind-sqli-time-based");
    expect(findings[0]!.severity).toBe("critical");
    expect(findings[0]!.metadata?.baselineMs).toBe(2000);
    expect(findings[0]!.metadata?.responseMs).toBe(7000);
    expect(findings[0]!.metadata?.confirmMs).toBe(7000);

    // Sanity: the old baseline*5 rule (needing >10000ms) would have missed this.
    expect(7000).toBeLessThan(2000 * 5);
  });

  it("detects time-based blind SQLi on a fast baseline", async () => {
    mockRequest.mockResolvedValue({ statusCode: 200, body: mockBody("ok") });

    // now() sequence (absolute ms):
    //   baseline1: 0 -> 50     (50ms)
    //   baseline2: 50 -> 100   (50ms)   => baselineMs = 50
    //   payload:   100 -> 6100 (6000ms) => delta 5950 -> trigger
    //   confirm:   6100 -> 12100 (6000ms) => delta 5950 -> finding
    const now = scriptedNow([0, 50, 50, 100, 100, 6100, 6100, 12100]);

    const findings = await detectTimeBased(makeEndpoint(), now);

    expect(findings.length).toBe(1);
    expect(findings[0]!.ruleId).toBe("fuzzer-blind-sqli-time-based");
    expect(findings[0]!.severity).toBe("critical");
    expect(findings[0]!.metadata?.baselineMs).toBe(50);
  });

  it("does NOT flag when only the first measurement is slow (transient)", async () => {
    mockRequest.mockResolvedValue({ statusCode: 200, body: mockBody("ok") });

    // First payload is slow (transient spike) but the confirmation is fast, so
    // no finding is emitted. Remaining payloads then measure 0ms (queue drained,
    // clock repeats last value) and never trigger.
    // now() sequence (absolute ms):
    //   baseline1: 0 -> 2000   (2000ms)
    //   baseline2: 2000 -> 4000 (2000ms)  => baselineMs = 2000
    //   payload1:  4000 -> 11000 (7000ms) => delta 5000 -> trigger
    //   confirm:   11000 -> 13000 (2000ms) => delta 0 -> NO finding
    //   (queue exhausted; every later now() returns 13000 => 0ms elapsed)
    const now = scriptedNow([0, 2000, 2000, 4000, 4000, 11000, 11000, 13000]);

    const findings = await detectTimeBased(makeEndpoint(), now);
    expect(findings.length).toBe(0);
  });

  it("returns no findings when responses are fast", async () => {
    mockRequest.mockResolvedValue({ statusCode: 200, body: mockBody("ok") });

    // Constant clock => every elapsed measurement is 0ms, nothing triggers.
    const findings = await detectTimeBased(makeEndpoint(), () => 0);
    expect(findings.length).toBe(0);
  });

  it("returns no findings for endpoints with no parameters", async () => {
    const findings = await detectTimeBased(makeEndpoint({ parameters: [] }), () => 0);
    expect(findings.length).toBe(0);
    expect(mockRequest).not.toHaveBeenCalled();
  });

  it("handles baseline request failure gracefully", async () => {
    mockRequest.mockRejectedValue(new Error("Connection refused"));

    const findings = await detectTimeBased(makeEndpoint(), () => 0);
    expect(findings.length).toBe(0);
  });
});

describe("detectBooleanBased", () => {
  beforeEach(() => {
    mockRequest.mockReset();
  });

  // The mock distinguishes the three request types by inspecting the
  // (decoded) request URL:
  //   - baseline uses the benign value "1"      → no " OR " in the URL
  //   - the FALSE condition contains "1=2"/"1'='2"
  //   - the TRUE condition is everything else with " OR "
  function mockByCondition(lengths: { baseline: number; trueLen: number; falseLen: number }) {
    mockRequest.mockImplementation((url: unknown) => {
      // URLSearchParams encodes spaces as "+", so normalise before matching.
      const u = decodeURIComponent(String(url).replace(/\+/g, " "));
      let len: number;
      if (!/ OR /.test(u)) {
        len = lengths.baseline; // benign baseline request
      } else if (/1'='2|1=2/.test(u)) {
        len = lengths.falseLen; // false-condition payload
      } else {
        len = lengths.trueLen; // true-condition payload
      }
      return Promise.resolve({ statusCode: 200, body: mockBody("A".repeat(len)) });
    });
  }

  it("flags boolean SQLi when true≈baseline and false differs materially", async () => {
    // baseline ≈ 1000, true ≈ 1005 (looks like baseline), false ≈ 400 (materially different)
    mockByCondition({ baseline: 1000, trueLen: 1005, falseLen: 400 });

    const findings = await detectBooleanBased(makeEndpoint());
    expect(findings.length).toBe(1);
    expect(findings[0]!.ruleId).toBe("fuzzer-blind-sqli-boolean-based");
    expect(findings[0]!.severity).toBe("high");
    expect(findings[0]!.metadata?.baselineLengthBytes).toBe(1000);
  });

  it("does NOT flag boolean SQLi when true and false both differ from baseline (normal dynamic page)", async () => {
    // baseline ≈ 1000, true ≈ 1300, false ≈ 1700 — true is NOT similar to baseline,
    // so despite true vs false differing >20% (which the OLD logic flagged) this is a
    // normal dynamic page and must NOT be reported.
    mockByCondition({ baseline: 1000, trueLen: 1300, falseLen: 1700 });

    const findings = await detectBooleanBased(makeEndpoint());
    expect(findings.length).toBe(0);
  });

  it("returns no findings when responses are similar in length", async () => {
    mockRequest.mockResolvedValue({
      statusCode: 200,
      body: mockBody("consistent response body here"),
    });

    const findings = await detectBooleanBased(makeEndpoint());
    expect(findings.length).toBe(0);
  });

  it("returns no findings for endpoints with no parameters", async () => {
    const findings = await detectBooleanBased(makeEndpoint({ parameters: [] }));
    expect(findings.length).toBe(0);
  });

  it("handles request failure gracefully", async () => {
    mockRequest.mockRejectedValue(new Error("Network error"));

    const findings = await detectBooleanBased(makeEndpoint());
    expect(findings.length).toBe(0);
  });
});
