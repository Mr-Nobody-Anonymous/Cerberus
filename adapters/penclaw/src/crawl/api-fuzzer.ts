import { request } from "undici";
import type { DiscoveredEndpoint, Payload, RawFinding, ScannerResult } from "../types/index.js";
import { assertHostAllowed, isBlockedHost } from "../utils/ssrf-guard.js";
import { loadPayloads } from "../utils/payloads.js";
import { getErrorMessage } from "../utils/errors.js";
import { USER_AGENT } from "../utils/constants.js";
import { Semaphore } from "../utils/http.js";

// ---------------------------------------------------------------------------
// Payload loading — prefer data/payloads/ files, fall back to the hardcoded
// payloads below if a category file is missing or fails to load.
// ---------------------------------------------------------------------------

function getPayloads(category: string): Payload[] {
  try {
    const loaded = loadPayloads(category);
    if (loaded.length > 0) return loaded;
  } catch {
    // fall through to built-in fallback
  }
  return fallbackPayloads[category] ?? [];
}

const fallbackPayloads: Record<string, Payload[]> = {
  sqli: [
    { value: "' OR '1'='1", technique: "error-based", description: "Classic OR injection" },
    { value: "1; DROP TABLE users--", technique: "stacked", description: "Stacked query" },
    { value: "' UNION SELECT NULL--", technique: "union-based", description: "Union probe" },
  ],
  xss: [
    { value: '<script>alert(1)</script>', technique: "html-context", description: "Script tag" },
    { value: '"><img src=x onerror=alert(1)>', technique: "attribute-context", description: "Attribute breakout" },
  ],
  ssrf: [
    { value: "http://169.254.169.254/latest/meta-data/", technique: "cloud-metadata", description: "AWS metadata" },
    { value: "http://metadata.google.internal/computeMetadata/v1/", technique: "cloud-metadata", description: "GCP metadata" },
    { value: "http://169.254.169.254/metadata/instance?api-version=2021-02-01", technique: "cloud-metadata", description: "Azure IMDS" },
    { value: "http://127.0.0.1/", technique: "localhost", description: "Localhost" },
    { value: "http://[::1]/", technique: "localhost", description: "IPv6 localhost" },
    { value: "http://0x7f000001/", technique: "localhost", description: "Hex localhost" },
    { value: "file:///etc/passwd", technique: "protocol-smuggling", description: "File protocol" },
  ],
  "path-traversal": [
    { value: "../../../etc/passwd", technique: "unix", description: "Unix path traversal" },
    { value: "..\\..\\..\\windows\\system32\\config\\sam", technique: "windows", description: "Windows path traversal" },
  ],
  nosql: [
    { value: '{"$gt":""}', technique: "operator-injection", description: "NoSQL $gt" },
    { value: '{"$ne":null}', technique: "operator-injection", description: "NoSQL $ne" },
  ],
  command: [
    { value: "; ls /", technique: "semicolon", description: "Semicolon injection" },
    { value: "| cat /etc/passwd", technique: "pipe", description: "Pipe injection" },
    { value: "$(whoami)", technique: "subshell", description: "Subshell injection" },
  ],
};

const injectionGroups = [
  { name: "sql-injection", category: "injection", payloadCategory: "sqli" },
  { name: "nosql-injection", category: "injection", payloadCategory: "nosql" },
  { name: "command-injection", category: "injection", payloadCategory: "command" },
  { name: "path-traversal", category: "path-traversal", payloadCategory: "path-traversal" },
  { name: "xss-reflected", category: "xss", payloadCategory: "xss" },
];

const authBypassHeaders: Array<{ name: string; headers: Record<string, string> }> = [
  { name: "X-Forwarded-For bypass", headers: { "X-Forwarded-For": "127.0.0.1" } },
  { name: "X-Original-URL bypass", headers: { "X-Original-URL": "/admin" } },
  { name: "X-Rewrite-URL bypass", headers: { "X-Rewrite-URL": "/admin" } },
];

// ---------------------------------------------------------------------------
// SSRF parameter names heuristic
// ---------------------------------------------------------------------------

const SSRF_PARAM_PATTERN = /^(url|uri|path|file|src|dest|redirect|next|target|link|callback|return|goto|ref)$/i;
const SSRF_RESPONSE_KEYWORDS = /ami-id|instance-id|computeMetadata|meta-data\/|iam\/security-credentials|placement\/availability-zone/i;

export function looksLikeSsrf(body: string): boolean {
  return SSRF_RESPONSE_KEYWORDS.test(body);
}

// ---------------------------------------------------------------------------
// Blind SQLi — time-based payloads
// ---------------------------------------------------------------------------

const TIME_BASED_PAYLOADS: Payload[] = [
  { value: "' OR SLEEP(5)-- ", technique: "time-based", description: "MySQL SLEEP", dbms: "mysql" },
  { value: "'; SELECT pg_sleep(5);-- ", technique: "time-based", description: "PostgreSQL pg_sleep", dbms: "postgresql" },
  { value: "'; WAITFOR DELAY '0:0:5';-- ", technique: "time-based", description: "MSSQL WAITFOR DELAY", dbms: "mssql" },
  { value: "' OR 1=1 AND SLEEP(5)-- ", technique: "time-based", description: "MySQL conditional SLEEP", dbms: "mysql" },
  { value: "1' AND (SELECT * FROM (SELECT SLEEP(5))a)-- ", technique: "time-based", description: "MySQL subquery SLEEP", dbms: "mysql" },
];

// ---------------------------------------------------------------------------
// Blind SQLi — boolean-based payloads (true/false pairs)
// ---------------------------------------------------------------------------

const BOOLEAN_PAIRS: Array<{ truePayload: Payload; falsePayload: Payload }> = [
  {
    truePayload: { value: "' OR '1'='1' -- ", technique: "boolean-based", description: "True condition" },
    falsePayload: { value: "' OR '1'='2' -- ", technique: "boolean-based", description: "False condition" },
  },
  {
    truePayload: { value: "1 OR 1=1", technique: "boolean-based", description: "Numeric true" },
    falsePayload: { value: "1 OR 1=2", technique: "boolean-based", description: "Numeric false" },
  },
  {
    truePayload: { value: "' OR 1=1#", technique: "boolean-based", description: "Hash-commented true" },
    falsePayload: { value: "' OR 1=2#", technique: "boolean-based", description: "Hash-commented false" },
  },
];

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function fuzzEndpoints(
  endpoints: DiscoveredEndpoint[],
  baseUrl: string,
  options?: {
    maxConcurrentRequests?: number;
    requestDelayMs?: number;
    auth?: { bearerToken?: string; cookieHeader?: string; bearerTokenB?: string };
    allowPrivate?: boolean;
  },
): Promise<ScannerResult> {
  const startedAt = Date.now();
  const warnings: string[] = [];
  const findings: RawFinding[] = [];

  const maxConcurrent = options?.maxConcurrentRequests ?? 10;
  const delayMs = options?.requestDelayMs ?? 0;
  const semaphore = new Semaphore(maxConcurrent);

  const limited = endpoints.slice(0, 30);

  // SSRF guard: filter out endpoints targeting private/internal hosts ONCE, up
  // front, so EVERY detector is protected (the host does not change within a
  // detector's requests). Endpoints can be attacker-influenced (the crawler
  // records cross-origin request URLs), so this must apply to all of them.
  const allowPrivate = options?.allowPrivate ?? false;
  const safeEndpoints = limited.filter((e) => {
    try { return allowPrivate || !isBlockedHost(new URL(e.url).hostname); }
    catch { return false; }
  });
  const skipped = limited.length - safeEndpoints.length;
  if (skipped > 0) warnings.push(`Skipped ${skipped} endpoint(s) targeting private/internal hosts (use --allow-private to include).`);

  try {
    const tasks: Array<Promise<void>> = [];

    for (const endpoint of safeEndpoints) {
      tasks.push(runWithSemaphore(semaphore, delayMs, async () => {
        findings.push(...await fuzzSingleEndpoint(endpoint, semaphore, delayMs));
      }));
      tasks.push(runWithSemaphore(semaphore, delayMs, async () => {
        findings.push(...await testAuthBypass(endpoint));
      }));
      tasks.push(runWithSemaphore(semaphore, delayMs, async () => {
        findings.push(...await testIdor(endpoint, options?.auth, options?.allowPrivate ?? false));
      }));
      tasks.push(runWithSemaphore(semaphore, delayMs, async () => {
        findings.push(...await detectTimeBased(endpoint));
      }));
      tasks.push(runWithSemaphore(semaphore, delayMs, async () => {
        findings.push(...await detectBooleanBased(endpoint));
      }));
      tasks.push(runWithSemaphore(semaphore, delayMs, async () => {
        findings.push(...await testSsrfParameters(endpoint));
      }));
    }

    await Promise.all(tasks);
  } catch (error) {
    warnings.push(`API fuzzing failed: ${getErrorMessage(error)}`);
  }

  return { scanner: "fuzzer", findings, warnings, executionMs: Date.now() - startedAt };
}

async function runWithSemaphore(semaphore: Semaphore, delayMs: number, fn: () => Promise<void>): Promise<void> {
  await semaphore.acquire();
  try {
    if (delayMs > 0) await delay(delayMs);
    await fn();
  } finally {
    semaphore.release();
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Classic injection fuzzing
// ---------------------------------------------------------------------------

async function fuzzSingleEndpoint(
  endpoint: DiscoveredEndpoint,
  semaphore: Semaphore,
  delayMs: number,
): Promise<RawFinding[]> {
  const findings: RawFinding[] = [];

  for (const group of injectionGroups) {
    const payloads = getPayloads(group.payloadCategory);
    for (const payload of payloads) {
      try {
        await semaphore.acquire();
        try {
          if (delayMs > 0) await delay(delayMs);
          const url = buildFuzzedUrl(endpoint.url, endpoint.parameters, payload.value);
          const { statusCode, body: bodyStream } = await request(url, {
            method: endpoint.method as "GET" | "POST",
            headers: {
              "User-Agent": USER_AGENT,
              "Content-Type": "application/x-www-form-urlencoded",
            },
            body: endpoint.method === "POST" ? buildPostBody(endpoint.parameters, payload.value) : undefined,
            signal: AbortSignal.timeout(5_000),
          });

          const body = await bodyStream.text();

          if (isErrorResponse(body, group.name)) {
            findings.push({
              id: `fuzz-${group.name}-${endpoint.url}-${findings.length}`,
              source: "fuzzer",
              ruleId: `fuzzer-${group.name}`,
              title: `Potential ${group.name} in ${endpoint.url}`,
              description: `The endpoint ${endpoint.url} returned an error response when injected with a ${group.name} payload, suggesting the input is not properly sanitized.`,
              severity: group.category === "injection" ? "high" : "medium",
              category: group.category,
              locations: [{ path: endpoint.url, snippet: payload.value }],
              metadata: {
                statusCode,
                payload: payload.value,
                technique: payload.technique,
                method: endpoint.method,
                responseSnippet: body.slice(0, 300),
              },
            });
            break; // One confirmed payload per group per endpoint
          }
        } finally {
          semaphore.release();
        }
      } catch {
        // Request failed — skip
      }
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Time-based blind SQLi detection
// ---------------------------------------------------------------------------

// The time-delay payloads all sleep for this many seconds. Detection is
// delta-based: a real injection adds ~SLEEP_SECONDS on top of the baseline,
// regardless of how slow the baseline itself is.
const SLEEP_SECONDS = 5;

export async function detectTimeBased(
  endpoint: DiscoveredEndpoint,
  now: () => number = Date.now,
): Promise<RawFinding[]> {
  const findings: RawFinding[] = [];
  if (endpoint.parameters.length === 0) return findings;

  // Measure baseline response time (average of 2 requests)
  let baselineMs: number;
  try {
    const times: number[] = [];
    for (let i = 0; i < 2; i++) {
      const start = now();
      const { body } = await request(endpoint.url, {
        method: endpoint.method as "GET" | "POST",
        headers: { "User-Agent": USER_AGENT },
        signal: AbortSignal.timeout(10_000),
      });
      await body.text();
      times.push(now() - start);
    }
    baselineMs = times.reduce((a, b) => a + b, 0) / times.length;
  } catch {
    return findings;
  }

  // The added delay must be close to the injected sleep (>=70% of it) and
  // clearly above ordinary jitter (>=2s). Delta-based, so it works even when
  // the baseline latency is high (the old baseline*5 rule missed those).
  const triggerThreshold = SLEEP_SECONDS * 1000 * 0.7;

  // Try time-delay payloads
  const payloads = getPayloads("sqli").filter((p) => p.technique === "time-based");
  const timingPayloads = payloads.length > 0 ? payloads : TIME_BASED_PAYLOADS;

  for (const payload of timingPayloads) {
    try {
      const url = buildFuzzedUrl(endpoint.url, endpoint.parameters, payload.value);
      // Shared request options for both the first and the confirmation request.
      const requestOptions = {
        method: endpoint.method as "GET" | "POST",
        headers: {
          "User-Agent": USER_AGENT,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: endpoint.method === "POST" ? buildPostBody(endpoint.parameters, payload.value) : undefined,
        signal: AbortSignal.timeout(15_000),
      };

      const start = now();
      const { body } = await request(url, requestOptions);
      await body.text();
      const elapsed = now() - start;
      const delta = elapsed - baselineMs;

      // Only worth a confirmation when the added delay is close to the sleep.
      if (delta >= triggerThreshold && delta >= 2_000) {
        // Re-run the SAME payload once to confirm — kills one-shot transient FPs.
        const confirmStart = now();
        const { body: confirmBody } = await request(url, requestOptions);
        await confirmBody.text();
        const confirmElapsed = now() - confirmStart;

        if (confirmElapsed - baselineMs >= triggerThreshold) {
          findings.push({
            id: `fuzz-blind-sqli-time-${endpoint.url}-${payload.dbms ?? "unknown"}`,
            source: "fuzzer",
            ruleId: "fuzzer-blind-sqli-time-based",
            title: `Time-based blind SQL injection in ${endpoint.url}`,
            description: `The endpoint responded in ${elapsed}ms (baseline: ${Math.round(baselineMs)}ms, confirmation: ${confirmElapsed}ms) when injected with a time-delay payload, confirming blind SQL injection.`,
            severity: "critical",
            category: "injection",
            locations: [{ path: endpoint.url, snippet: payload.value }],
            metadata: {
              payload: payload.value,
              technique: "time-based-blind",
              dbms: payload.dbms,
              baselineMs: Math.round(baselineMs),
              responseMs: elapsed,
              confirmMs: confirmElapsed,
              method: endpoint.method,
            },
          });
          break; // One confirmed is enough
        }
      }
    } catch {
      // Timeout or error — might also indicate success but we play safe
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Boolean-based blind SQLi detection
// ---------------------------------------------------------------------------

function lenSimilar(a: number, b: number): boolean {
  const max = Math.max(a, b);
  if (max === 0) return true;
  return Math.abs(a - b) / max <= 0.1;
}

export async function detectBooleanBased(endpoint: DiscoveredEndpoint): Promise<RawFinding[]> {
  const findings: RawFinding[] = [];
  if (endpoint.parameters.length === 0) return findings;

  // Establish a BASELINE with a benign parameter value. Boolean-blind SQLi is
  // only credible when the TRUE condition looks like this normal page while the
  // FALSE condition materially differs. Without a baseline, two different query
  // values on a normal dynamic page routinely differ >20% → false positives.
  let baselineLen: number;
  try {
    const baselineUrl = buildFuzzedUrl(endpoint.url, endpoint.parameters, "1");
    const baselineResp = await request(baselineUrl, {
      method: endpoint.method as "GET" | "POST",
      headers: {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: endpoint.method === "POST" ? buildPostBody(endpoint.parameters, "1") : undefined,
      signal: AbortSignal.timeout(5_000),
    });
    baselineLen = (await baselineResp.body.text()).length;
  } catch {
    // Can't establish a baseline → no reliable detection.
    return findings;
  }

  for (const pair of BOOLEAN_PAIRS) {
    try {
      const trueUrl = buildFuzzedUrl(endpoint.url, endpoint.parameters, pair.truePayload.value);
      const falseUrl = buildFuzzedUrl(endpoint.url, endpoint.parameters, pair.falsePayload.value);

      const [trueResp, falseResp] = await Promise.all([
        request(trueUrl, {
          method: endpoint.method as "GET" | "POST",
          headers: {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: endpoint.method === "POST" ? buildPostBody(endpoint.parameters, pair.truePayload.value) : undefined,
          signal: AbortSignal.timeout(5_000),
        }),
        request(falseUrl, {
          method: endpoint.method as "GET" | "POST",
          headers: {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: endpoint.method === "POST" ? buildPostBody(endpoint.parameters, pair.falsePayload.value) : undefined,
          signal: AbortSignal.timeout(5_000),
        }),
      ]);

      const trueBody = await trueResp.body.text();
      const falseBody = await falseResp.body.text();

      const trueLen = trueBody.length;
      const falseLen = falseBody.length;

      // 3-way comparison against the baseline: a real boolean-blind SQLi shows
      // the TRUE condition matching the normal (baseline) page AND the FALSE
      // condition materially differing from it. A sanity check ensures the
      // true/false responses themselves also differ (>10%).
      const maxTrueFalse = Math.max(trueLen, falseLen);
      const trueFalseDiff = maxTrueFalse === 0 ? 0 : Math.abs(trueLen - falseLen) / maxTrueFalse;

      if (lenSimilar(baselineLen, trueLen) && !lenSimilar(baselineLen, falseLen) && trueFalseDiff > 0.1) {
        const diff = trueFalseDiff;
        findings.push({
          id: `fuzz-blind-sqli-boolean-${endpoint.url}-${findings.length}`,
          source: "fuzzer",
          ruleId: "fuzzer-blind-sqli-boolean-based",
          title: `Potential boolean-based blind SQL injection in ${endpoint.url}`,
          description: `Compared against a benign baseline (${baselineLen} bytes): the true-condition response matched the baseline (${trueLen} bytes) while the false-condition response materially differed (${falseLen} bytes), a ${Math.round(diff * 100)}% true/false body-length difference, suggesting boolean-based blind SQL injection.`,
          severity: "high",
          category: "injection",
          locations: [{ path: endpoint.url, snippet: pair.truePayload.value }],
          metadata: {
            truePayload: pair.truePayload.value,
            falsePayload: pair.falsePayload.value,
            technique: "boolean-based-blind",
            baselineLengthBytes: baselineLen,
            trueLengthBytes: trueLen,
            falseLengthBytes: falseLen,
            diffPercent: Math.round(diff * 100),
            method: endpoint.method,
          },
        });
        break;
      }
    } catch {
      // Skip
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// SSRF testing
// ---------------------------------------------------------------------------

export async function testSsrfParameters(endpoint: DiscoveredEndpoint): Promise<RawFinding[]> {
  const findings: RawFinding[] = [];

  const ssrfParams = endpoint.parameters.filter((p) => SSRF_PARAM_PATTERN.test(p));
  if (ssrfParams.length === 0) return findings;

  const payloads = getPayloads("ssrf");
  const ssrfPayloads = payloads.length > 0 ? payloads : (fallbackPayloads["ssrf"] ?? []);

  for (const param of ssrfParams) {
    for (const payload of ssrfPayloads) {
      try {
        const urlObj = new URL(endpoint.url);
        urlObj.searchParams.set(param, payload.value);

        const { body: bodyStream } = await request(urlObj.href, {
          method: endpoint.method as "GET" | "POST",
          headers: {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: endpoint.method === "POST" ? `${encodeURIComponent(param)}=${encodeURIComponent(payload.value)}` : undefined,
          signal: AbortSignal.timeout(5_000),
        });

        const body = await bodyStream.text();

        if (looksLikeSsrf(body)) {
          findings.push({
            id: `fuzz-ssrf-${param}-${endpoint.url}-${findings.length}`,
            source: "fuzzer",
            ruleId: "fuzzer-ssrf",
            title: `SSRF detected via parameter '${param}' in ${endpoint.url}`,
            description: `The parameter '${param}' accepted an SSRF payload and the response contained cloud metadata or internal resource indicators.`,
            severity: "critical",
            category: "ssrf",
            locations: [{ path: endpoint.url, snippet: `${param}=${payload.value}` }],
            metadata: {
              parameter: param,
              payload: payload.value,
              technique: payload.technique,
              method: endpoint.method,
              responseSnippet: body.slice(0, 300),
            },
          });
          break; // One confirmed per param is enough
        }
      } catch {
        // Skip
      }
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Auth bypass + IDOR (unchanged logic, kept for completeness)
// ---------------------------------------------------------------------------

async function testAuthBypass(endpoint: DiscoveredEndpoint): Promise<RawFinding[]> {
  const findings: RawFinding[] = [];

  let baselineStatus: number;
  try {
    const { statusCode } = await request(endpoint.url, {
      method: endpoint.method as "GET" | "POST",
      headers: { "User-Agent": USER_AGENT },
      signal: AbortSignal.timeout(5_000),
    });
    baselineStatus = statusCode;
  } catch {
    return findings;
  }

  if (baselineStatus === 200) return findings;

  for (const bypass of authBypassHeaders) {
    try {
      const { statusCode } = await request(endpoint.url, {
        method: endpoint.method as "GET" | "POST",
        headers: {
          "User-Agent": USER_AGENT,
          ...bypass.headers,
        },
        signal: AbortSignal.timeout(5_000),
      });

      if (statusCode === 200 && baselineStatus !== 200) {
        findings.push({
          id: `fuzz-auth-bypass-${bypass.name}-${endpoint.url}`,
          source: "fuzzer",
          ruleId: "fuzzer-auth-bypass",
          title: `Authentication bypass via ${bypass.name}`,
          description: `The endpoint ${endpoint.url} returned 200 when using ${bypass.name} header, but returned ${baselineStatus} without it.`,
          severity: "critical",
          category: "auth-bypass",
          locations: [{ path: endpoint.url, snippet: JSON.stringify(bypass.headers) }],
          metadata: { bypassMethod: bypass.name, baselineStatus, bypassStatus: statusCode },
        });
      }
    } catch {
      // Skip
    }
  }

  return findings;
}

function identityHeaders(token?: string, cookie?: string): Record<string, string> {
  const h: Record<string, string> = { "User-Agent": USER_AGENT };
  if (token) h["Authorization"] = `Bearer ${token}`;
  if (cookie) h["Cookie"] = cookie;
  return h;
}

export async function testIdor(
  endpoint: DiscoveredEndpoint,
  auth?: { bearerToken?: string; cookieHeader?: string; bearerTokenB?: string },
  allowPrivate = false,
): Promise<RawFinding[]> {
  const findings: RawFinding[] = [];

  const idMatch = endpoint.url.match(/\/(\d+)(?:\/|$|\?)/);
  if (!idMatch) return findings;
  const originalId = idMatch[1]!;

  // No-auth mode: SKIP entirely. Unauthenticated ID-diffing (a different ID
  // returning different 200 content) is normal public-resource behavior, not
  // an authorization failure, so it cannot indicate IDOR — pure noise.
  const hasAuth = Boolean(auth?.bearerToken || auth?.cookieHeader);
  if (!hasAuth) return findings;

  const headersA = identityHeaders(auth?.bearerToken, auth?.cookieHeader);

  // Mode 1: two-identity (STRONG). GET identity A's resource, then re-request
  // the SAME URL as identity B. If B can read it too, that is a confirmed
  // broken object-level authorization (IDOR).
  if (auth?.bearerTokenB) {
    try {
      assertHostAllowed(endpoint.url, allowPrivate);
      const { statusCode: statusA, body: bodyAStream } = await request(endpoint.url, {
        method: "GET",
        headers: headersA,
        signal: AbortSignal.timeout(5_000),
      });
      const bodyA = await bodyAStream.text();
      if (statusA !== 200) return findings;

      assertHostAllowed(endpoint.url, allowPrivate);
      const { statusCode: statusB, body: bodyBStream } = await request(endpoint.url, {
        method: "GET",
        headers: identityHeaders(auth.bearerTokenB),
        signal: AbortSignal.timeout(5_000),
      });
      const bodyB = await bodyBStream.text();

      // B must succeed AND return content resembling A's resource. lenSimilar
      // (±10%) plus a non-trivial length guard avoids matching empty/error pages.
      if (statusB === 200 && bodyB.length > 50 && lenSimilar(bodyA.length, bodyB.length)) {
        findings.push({
          id: `fuzz-idor-${endpoint.url}`,
          source: "fuzzer",
          ruleId: "fuzzer-idor",
          title: "IDOR confirmed: identity B can read identity A's resource",
          description: `A second authenticated identity (B) received a 200 response with content similar to identity A's for ${endpoint.url}, confirming broken object-level authorization (IDOR).`,
          severity: "high",
          category: "idor",
          locations: [{ path: endpoint.url }],
          metadata: { url: endpoint.url, identityAStatus: 200, identityBStatus: 200 },
        });
      }
    } catch {
      // Skip
    }
    return findings;
  }

  // Mode 2: single-identity. With one identity we can only flag that an
  // authenticated user could read another record — weaker than mode 1, so
  // medium severity and a nudge to re-run with a second identity.
  const testIds = [
    String(Number(originalId) + 1),
    String(Number(originalId) - 1),
    "1",
    "0",
  ];

  try {
    assertHostAllowed(endpoint.url, allowPrivate);
    const { statusCode: originalStatus, body: originalBody } = await request(endpoint.url, {
      method: "GET",
      headers: headersA,
      signal: AbortSignal.timeout(5_000),
    });
    const originalText = await originalBody.text();
    if (originalStatus !== 200) return findings;

    for (const testId of testIds) {
      const testUrl = endpoint.url.replace(`/${originalId}`, `/${testId}`);
      try {
        assertHostAllowed(testUrl, allowPrivate);
        const { statusCode, body: testBody } = await request(testUrl, {
          method: "GET",
          headers: headersA,
          signal: AbortSignal.timeout(5_000),
        });
        const testText = await testBody.text();

        if (statusCode === 200 && testText !== originalText && testText.length > 50) {
          findings.push({
            id: `fuzz-idor-${endpoint.url}-${testId}`,
            source: "fuzzer",
            ruleId: "fuzzer-idor",
            title: "Likely IDOR: authenticated user accessed another record (verify with --auth-bearer-b)",
            description: `An authenticated request changed the ID from ${originalId} to ${testId} and received distinct 200 content, suggesting missing object-level authorization. Re-run with --auth-bearer-b to confirm.`,
            severity: "medium",
            category: "idor",
            locations: [{ path: testUrl }],
            metadata: { originalId, testId, unconfirmed: true },
          });
          break;
        }
      } catch {
        // Skip
      }
    }
  } catch {
    // Skip
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildFuzzedUrl(url: string, params: string[], payload: string): string {
  if (params.length === 0) return url;
  const urlObj = new URL(url);
  for (const param of params) {
    urlObj.searchParams.set(param, payload);
  }
  return urlObj.href;
}

function buildPostBody(params: string[], payload: string): string {
  if (params.length === 0) return `test=${encodeURIComponent(payload)}`;
  return params.map((p) => `${encodeURIComponent(p)}=${encodeURIComponent(payload)}`).join("&");
}

export function isErrorResponse(body: string, payloadType: string): boolean {
  if (payloadType.includes("sql")) {
    return /sql syntax|syntax error|unclosed quotation|ORA-\d|ODBC|SQLSTATE|PG::|psql:|SQLite3::|mysqli?_/i.test(body);
  }
  if (payloadType.includes("command")) {
    return /root:.*:0:0:|uid=\d+\(|\/etc\/passwd|drwx/i.test(body);
  }
  if (payloadType.includes("path")) {
    return /root:.*:0:0:|\/etc\/passwd|\[boot loader\]|NTLDR/i.test(body);
  }
  if (payloadType.includes("xss")) {
    return body.includes("<script>alert(1)</script>") || body.includes('onerror=alert(1)');
  }
  return false;
}
