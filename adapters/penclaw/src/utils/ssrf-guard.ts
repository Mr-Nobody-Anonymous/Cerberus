/**
 * SSRF guard: refuse connections to loopback, private, link-local, and cloud
 * metadata endpoints unless the operator explicitly opts in (--allow-private).
 * Best-effort host-based check (DNS rebinding is out of scope).
 */

const BLOCKED_HOSTNAMES = new Set(["localhost", "metadata.google.internal"]);

/**
 * Parse a single dotted-quad part or a bare integer that may be expressed in
 * decimal, 0x-prefixed hex, or 0-prefixed octal.
 */
function parseIntRadix(p: string): number | null {
  if (/^0x[0-9a-f]+$/i.test(p)) return parseInt(p, 16);
  if (/^0[0-7]+$/.test(p)) return parseInt(p, 8);
  if (/^\d+$/.test(p)) return parseInt(p, 10);
  return null;
}

/**
 * Canonicalize any IPv4 representation to dotted-quad octets so private-range
 * checks cannot be bypassed with alternate encodings. Handles dotted decimal/
 * octal/hex, a bare 32-bit integer (decimal or hex), and IPv4-mapped IPv6
 * (::ffff:127.0.0.1 and ::ffff:7f00:1). Returns null for non-IPv4 hosts.
 */
function toIPv4Octets(host: string): number[] | null {
  // Strip IPv4-mapped IPv6 prefix: ::ffff:127.0.0.1  or  ::ffff:7f00:1
  let h = host;
  const mapped = h.match(/^::ffff:(.+)$/i);
  if (mapped) {
    const rest = mapped[1];
    // hex form like 7f00:1 -> combine two 16-bit groups
    const hexGroups = rest.match(/^([0-9a-f]{1,4}):([0-9a-f]{1,4})$/i);
    if (hexGroups) {
      const hi = parseInt(hexGroups[1], 16);
      const lo = parseInt(hexGroups[2], 16);
      return [(hi >> 8) & 255, hi & 255, (lo >> 8) & 255, lo & 255];
    }
    h = rest; // fall through to dotted/decimal parsing on the tail
  }

  // Dotted form: each part may be decimal, 0x-hex, or 0-octal
  if (h.includes(".")) {
    const parts = h.split(".");
    if (parts.length !== 4) return null;
    const octets: number[] = [];
    for (const p of parts) {
      const n = parseIntRadix(p);
      if (n === null || n > 255) return null;
      octets.push(n);
    }
    return octets;
  }

  // Bare integer (decimal or hex): a single 32-bit number
  const n = parseIntRadix(h);
  if (n === null || n < 0 || n > 0xffffffff) return null;
  return [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255];
}

export function isBlockedHost(host: string): boolean {
  // NOTE: DNS rebinding (a public hostname that resolves to a private IP) is
  // intentionally out of scope — this is a best-effort host-string check.
  const h = host.toLowerCase().replace(/^\[|\]$/g, ""); // strip IPv6 brackets
  if (BLOCKED_HOSTNAMES.has(h)) return true;
  // IPv6 literals only — gate on a colon so public hostnames like "fc2.com" or
  // "fe80shop.com" are not caught by the fc/fd/fe80 prefix checks.
  if (h.includes(":")) {
    if (h === "::" || h === "::1") return true;                 // unspecified + loopback
    if (h.startsWith("fc") || h.startsWith("fd")) return true;  // fc00::/7 unique local
    if (h.startsWith("fe80")) return true;                      // link-local
    // fall through: IPv4-mapped IPv6 (::ffff:...) is handled by toIPv4Octets below
  }
  const ip = toIPv4Octets(h);
  if (!ip) return false;
  const [a, b] = ip;
  if (a === 127) return true;
  if (a === 10) return true;
  if (a === 192 && b === 168) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 169 && b === 254) return true;
  if (a === 0) return true;
  return false;
}

export function assertHostAllowed(urlString: string, allowPrivate: boolean): void {
  if (allowPrivate) return;
  let host: string;
  try {
    host = new URL(urlString).hostname;
  } catch {
    throw new Error(`Invalid URL: ${urlString}`);
  }
  if (isBlockedHost(host)) {
    throw new Error(`Refusing to connect to private/internal host '${host}'. Use --allow-private to override.`);
  }
}
