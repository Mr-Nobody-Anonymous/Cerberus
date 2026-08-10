import { describe, it, expect, vi, beforeEach } from "vitest";
import type { DiscoveredEndpoint } from "../src/types/index.js";

// Mock undici's request before importing the module under test.
const mockRequest = vi.fn();

vi.mock("undici", () => ({
  request: (...args: unknown[]) => mockRequest(...args),
}));

const { fuzzEndpoints } = await import("../src/crawl/api-fuzzer.js");

function mockBody(text: string) {
  return { text: () => Promise.resolve(text) };
}

function makeEndpoint(overrides?: Partial<DiscoveredEndpoint>): DiscoveredEndpoint {
  return {
    url: "http://example.com/api/x.json",
    method: "GET",
    parameters: ["q"],
    ...overrides,
  };
}

describe("fuzzEndpoints SSRF guard (private-host endpoints)", () => {
  beforeEach(() => {
    mockRequest.mockReset();
    mockRequest.mockResolvedValue({ statusCode: 200, body: mockBody("ok") });
  });

  it("never fuzzes an endpoint targeting the cloud metadata host and warns about skipping it", async () => {
    const metadataEndpoint = makeEndpoint({ url: "http://169.254.169.254/api/x.json" });

    const result = await fuzzEndpoints([metadataEndpoint], "http://example.com", {});

    // The metadata host must NEVER be contacted by ANY detector.
    const metadataCalls = mockRequest.mock.calls.filter(([url]) =>
      String(url).includes("169.254.169.254"),
    );
    expect(metadataCalls.length).toBe(0);

    // A warning must explain the skip.
    expect(result.warnings.some((w) => /private\/internal hosts/i.test(w))).toBe(true);
  });

  it("positive control: a public endpoint IS fuzzed (request is called for it)", async () => {
    const publicEndpoint = makeEndpoint({ url: "http://example.com/api/x.json" });

    const result = await fuzzEndpoints([publicEndpoint], "http://example.com", {});

    const publicCalls = mockRequest.mock.calls.filter(([url]) =>
      String(url).includes("example.com"),
    );
    expect(publicCalls.length).toBeGreaterThan(0);
    expect(result.warnings.some((w) => /private\/internal hosts/i.test(w))).toBe(false);
  });

  it("includes the private host when allowPrivate is set", async () => {
    const metadataEndpoint = makeEndpoint({ url: "http://169.254.169.254/api/x.json" });

    await fuzzEndpoints([metadataEndpoint], "http://example.com", { allowPrivate: true });

    const metadataCalls = mockRequest.mock.calls.filter(([url]) =>
      String(url).includes("169.254.169.254"),
    );
    expect(metadataCalls.length).toBeGreaterThan(0);
  });
});
