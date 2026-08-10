import type { CrawlResult, DiscoveredEndpoint, DynamicScanConfig, RawFinding, ScannerResult } from "../types/index.js";
import { createHmac } from "node:crypto";
import { request } from "undici";
import { assertHostAllowed } from "../utils/ssrf-guard.js";
import { getErrorMessage } from "../utils/errors.js";
import { USER_AGENT } from "../utils/constants.js";

const REQUEST_TIMEOUT_MS = 5_000;
const MAX_PROBE_ENDPOINTS = 10;
const MAX_REPLAY_REQUESTS = 20;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const JWT_REGEX = /eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*/g;

const COMMON_SECRETS = [
  "", "secret", "password", "key", "123456", "jwt_secret", "changeme",
  "admin", "test", "default", "jwt", "token", "s3cr3t", "pass",
  "qwerty", "letmein", "welcome", "monkey", "abc123", "supersecret",
];

// --- Base64url helpers (no deps) ---

function base64urlEncode(data: string): string {
  return Buffer.from(data, "utf-8")
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function base64urlDecode(str: string): string {
  // Restore standard base64
  let base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  while (base64.length % 4 !== 0) base64 += "=";
  return Buffer.from(base64, "base64").toString("utf-8");
}

function decodeJwtParts(jwt: string): { header: Record<string, unknown>; payload: Record<string, unknown>; signature: string } | null {
  const parts = jwt.split(".");
  if (parts.length < 2) return null;
  try {
    const header = JSON.parse(base64urlDecode(parts[0]!)) as Record<string, unknown>;
    const payload = JSON.parse(base64urlDecode(parts[1]!)) as Record<string, unknown>;
    return { header, payload, signature: parts[2] ?? "" };
  } catch {
    return null;
  }
}

function signHs256(headerB64: string, payloadB64: string, secret: string): string {
  const data = `${headerB64}.${payloadB64}`;
  return createHmac("sha256", secret)
    .update(data)
    .digest("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function buildToken(header: Record<string, unknown>, payload: Record<string, unknown>, secret?: string): string {
  const headerB64 = base64urlEncode(JSON.stringify(header));
  const payloadB64 = base64urlEncode(JSON.stringify(payload));
  if (secret === undefined) {
    // No signature (alg:none)
    return `${headerB64}.${payloadB64}.`;
  }
  const sig = signHs256(headerB64, payloadB64, secret);
  return `${headerB64}.${payloadB64}.${sig}`;
}

// --- JWT extraction ---

function extractJwts(crawlResult: CrawlResult): string[] {
  const jwts = new Set<string>();

  for (const page of crawlResult.pages) {
    // Check page URL for JWTs (rare but possible)
    for (const match of page.url.matchAll(JWT_REGEX)) {
      jwts.add(match[0]);
    }
  }

  for (const endpoint of crawlResult.endpoints) {
    if (endpoint.headers) {
      for (const value of Object.values(endpoint.headers)) {
        for (const match of value.matchAll(JWT_REGEX)) {
          jwts.add(match[0]);
        }
      }
    }
  }

  return [...jwts];
}

// --- Test functions ---

function checkMissingClaims(jwt: string, decoded: ReturnType<typeof decodeJwtParts>): RawFinding[] {
  if (!decoded) return [];
  const findings: RawFinding[] = [];
  const requiredClaims = ["exp", "iat", "iss"] as const;
  const missing = requiredClaims.filter((c) => !(c in decoded.payload));

  if (missing.length > 0) {
    findings.push({
      id: `jwt-missing-claims-${missing.join("-")}`,
      source: "jwt",
      ruleId: "jwt-missing-claims",
      title: `JWT missing recommended claims: ${missing.join(", ")}`,
      description: `The JWT is missing claims: ${missing.join(", ")}. These claims help prevent token misuse.`,
      severity: "low",
      category: "jwt-security",
      locations: [{ path: "JWT token", snippet: jwt.slice(0, 80) + "..." }],
      metadata: { missingClaims: missing },
    });
  }

  return findings;
}

function buildAlgNoneTokens(decoded: ReturnType<typeof decodeJwtParts>): string[] {
  if (!decoded) return [];
  const tokens: string[] = [];
  for (const alg of ["none", "None", "NONE", "nOnE"]) {
    tokens.push(buildToken({ ...decoded.header, alg }, decoded.payload));
  }
  return tokens;
}

// --- Active confirmation against the target ---

interface ProbedEndpoint {
  url: string;
  status: number;
}

interface ReplayBudget {
  count: number;
}

/**
 * GET (with NO auth header) up to the first ~10 endpoints plus the baseUrl.
 * Endpoints that reply 401/403 require authentication — those are the ones a
 * forged/expired token can be replayed against. Every request is SSRF-guarded.
 */
async function probeEndpointsDetailed(
  endpoints: DiscoveredEndpoint[],
  baseUrl: string,
  allowPrivate: boolean,
): Promise<ProbedEndpoint[]> {
  const urls = new Set<string>();
  if (baseUrl) urls.add(baseUrl);
  for (const ep of endpoints.slice(0, MAX_PROBE_ENDPOINTS)) urls.add(ep.url);

  const protectedEndpoints: ProbedEndpoint[] = [];
  for (const url of urls) {
    try {
      assertHostAllowed(url, allowPrivate);
      const res = await request(url, {
        method: "GET",
        headers: { "User-Agent": USER_AGENT },
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
      const status = res.statusCode;
      try { await res.body?.dump?.(); } catch { /* ignore */ }
      if (status === 401 || status === 403) {
        protectedEndpoints.push({ url, status });
      }
    } catch {
      // Swallow per-request errors (SSRF guard, timeouts, connection errors).
    }
  }
  return protectedEndpoints;
}

/**
 * Replay a token as `Authorization: Bearer <token>` against a URL.
 * Returns the HTTP status code, or -1 on error. SSRF-guarded.
 */
async function replayToken(url: string, token: string, allowPrivate: boolean): Promise<number> {
  try {
    assertHostAllowed(url, allowPrivate);
    const res = await request(url, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}`, "User-Agent": USER_AGENT },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    const status = res.statusCode;
    try { await res.body?.dump?.(); } catch { /* ignore */ }
    return status;
  } catch {
    return -1;
  }
}

async function confirmAlgNone(
  decoded: ReturnType<typeof decodeJwtParts>,
  protectedEndpoints: ProbedEndpoint[],
  allowPrivate: boolean,
  requestDelayMs: number | undefined,
  budget: ReplayBudget,
): Promise<RawFinding | null> {
  if (!decoded) return null;
  const tokens = buildAlgNoneTokens(decoded);
  const target = protectedEndpoints[0];

  if (target && tokens.length > 0) {
    for (const token of tokens) {
      if (budget.count >= MAX_REPLAY_REQUESTS) break;
      if (requestDelayMs) await delay(requestDelayMs);
      budget.count++;
      const status = await replayToken(target.url, token, allowPrivate);
      if (status === 200) {
        return {
          id: "jwt-alg-none-bypass",
          source: "jwt",
          ruleId: "jwt-alg-none",
          title: "JWT alg:none accepted — authentication bypass confirmed",
          description: `The server accepted a forged JWT with alg:"none" and an empty signature on protected endpoint ${target.url} (returned 200 where an unauthenticated request returned ${target.status}). This is a critical authentication bypass.`,
          severity: "critical",
          category: "jwt-security",
          locations: [{ path: "JWT token", snippet: token.slice(0, 80) + "..." }],
          metadata: {
            endpoint: target.url,
            statusUnauthenticated: target.status,
            statusWithForgedToken: 200,
            originalAlg: decoded.header.alg,
            testTokens: tokens,
          },
        };
      }
    }
  }

  // Not confirmed — emit a low-confidence candidate that triage will drop.
  return {
    id: "jwt-alg-none-bypass",
    source: "jwt",
    ruleId: "jwt-alg-none",
    title: "JWT alg:none candidate — not confirmed",
    description: `A forged JWT with alg:"none" was crafted, but the server did not accept it on any protected endpoint (or none were found). Reported as an unconfirmed candidate.`,
    severity: "info",
    category: "jwt-security",
    locations: [{ path: "JWT token", snippet: tokens[0]?.slice(0, 80) + "..." }],
    metadata: {
      originalAlg: decoded.header.alg,
      testTokens: tokens,
      unconfirmed: true,
    },
  };
}

async function confirmExpired(
  jwt: string,
  decoded: ReturnType<typeof decodeJwtParts>,
  protectedEndpoints: ProbedEndpoint[],
  allowPrivate: boolean,
  requestDelayMs: number | undefined,
  budget: ReplayBudget,
): Promise<RawFinding | null> {
  if (!decoded) return null;
  const exp = decoded.payload.exp;
  if (typeof exp !== "number") return null;
  const now = Math.floor(Date.now() / 1000);
  if (exp >= now) return null; // Only relevant when the token is actually expired.

  const target = protectedEndpoints[0];
  let accepted = false;
  if (target && budget.count < MAX_REPLAY_REQUESTS) {
    if (requestDelayMs) await delay(requestDelayMs);
    budget.count++;
    const status = await replayToken(target.url, jwt, allowPrivate);
    accepted = status === 200;
  }

  if (accepted && target) {
    return {
      id: "jwt-expired-accepted",
      source: "jwt",
      ruleId: "jwt-expired-accepted",
      title: "Expired JWT accepted by server",
      description: `The server accepted an expired JWT (exp=${exp}, expired ${Math.floor((now - exp) / 3600)} hours ago) on protected endpoint ${target.url} (returned 200 where an unauthenticated request returned ${target.status}). Expiration is not being validated.`,
      severity: "high",
      category: "jwt-security",
      locations: [{ path: "JWT token", snippet: jwt.slice(0, 80) + "..." }],
      metadata: {
        exp,
        expiredAgo: now - exp,
        endpoint: target.url,
        statusUnauthenticated: target.status,
        statusWithExpiredToken: 200,
      },
    };
  }

  return {
    id: "jwt-expired-accepted",
    source: "jwt",
    ruleId: "jwt-expired-accepted",
    title: "Expired JWT candidate — not confirmed by server",
    description: `An expired JWT (exp=${exp}, expired ${Math.floor((now - exp) / 3600)} hours ago) was found, but the server did not accept it on any protected endpoint (or none were found). Reported as an unconfirmed candidate.`,
    severity: "info",
    category: "jwt-security",
    locations: [{ path: "JWT token", snippet: jwt.slice(0, 80) + "..." }],
    metadata: {
      exp,
      expiredAgo: now - exp,
      unconfirmed: true,
    },
  };
}

function checkWeakSecret(jwt: string, decoded: ReturnType<typeof decodeJwtParts>): RawFinding[] {
  if (!decoded) return [];
  const alg = String(decoded.header.alg ?? "").toUpperCase();
  if (alg !== "HS256") return [];

  const parts = jwt.split(".");
  if (parts.length < 3) return [];

  const headerB64 = parts[0]!;
  const payloadB64 = parts[1]!;
  const originalSig = parts[2]!;

  for (const secret of COMMON_SECRETS) {
    const testSig = signHs256(headerB64, payloadB64, secret);
    if (testSig === originalSig) {
      return [{
        id: `jwt-weak-secret-${secret || "empty"}`,
        source: "jwt",
        ruleId: "jwt-weak-secret",
        title: `JWT signed with weak secret: "${secret || "(empty string)"}"`,
        description: `The JWT HS256 signature was successfully verified using the secret "${secret || "(empty string)"}". An attacker can forge arbitrary tokens.`,
        severity: "critical",
        category: "jwt-security",
        locations: [{ path: "JWT token", snippet: jwt.slice(0, 80) + "..." }],
        metadata: { secret, alg },
      }];
    }
  }

  return [];
}

// --- Main export ---

export async function testJwtSecurity(
  crawlResult: CrawlResult,
  config: DynamicScanConfig,
): Promise<ScannerResult> {
  const startedAt = Date.now();
  const warnings: string[] = [];
  const findings: RawFinding[] = [];
  const allowPrivate = config.allowPrivate ?? false;
  const requestDelayMs = config.requestDelayMs;

  try {
    const jwts = extractJwts(crawlResult);

    if (jwts.length === 0) {
      return { scanner: "jwt", findings: [], warnings: [], executionMs: Date.now() - startedAt };
    }

    // Probe once per scan: which endpoints require auth (candidates for replay)?
    const protectedEndpoints = await probeEndpointsDetailed(
      crawlResult.endpoints,
      config.baseUrl,
      allowPrivate,
    );
    const budget: ReplayBudget = { count: 0 };

    for (const jwt of jwts) {
      const decoded = decodeJwtParts(jwt);
      if (!decoded) continue;

      // Missing claims check (local, low severity)
      findings.push(...checkMissingClaims(jwt, decoded));

      // Expired token — actively confirm acceptance before reporting HIGH
      const expired = await confirmExpired(jwt, decoded, protectedEndpoints, allowPrivate, requestDelayMs, budget);
      if (expired) findings.push(expired);

      // alg:none bypass — actively confirm acceptance before reporting CRITICAL
      const algNone = await confirmAlgNone(decoded, protectedEndpoints, allowPrivate, requestDelayMs, budget);
      if (algNone) findings.push(algNone);

      // Weak secret brute force (cryptographically confirmed locally)
      findings.push(...checkWeakSecret(jwt, decoded));
    }
  } catch (error) {
    warnings.push(`JWT testing failed: ${getErrorMessage(error)}`);
  }

  return { scanner: "jwt", findings, warnings, executionMs: Date.now() - startedAt };
}

// Exported for testing
export { decodeJwtParts, buildToken, signHs256, base64urlEncode, base64urlDecode, extractJwts, buildAlgNoneTokens, COMMON_SECRETS };
