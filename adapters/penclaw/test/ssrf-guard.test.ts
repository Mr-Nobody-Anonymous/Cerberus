import { describe, it, expect } from "vitest";
import { isBlockedHost } from "../src/utils/ssrf-guard.js";

describe("isBlockedHost", () => {
  it("blocks loopback", () => {
    expect(isBlockedHost("127.0.0.1")).toBe(true);
    expect(isBlockedHost("localhost")).toBe(true);
    expect(isBlockedHost("::1")).toBe(true);
  });
  it("blocks the cloud metadata IP", () => {
    expect(isBlockedHost("169.254.169.254")).toBe(true);
  });
  it("blocks RFC1918 ranges", () => {
    expect(isBlockedHost("10.0.0.5")).toBe(true);
    expect(isBlockedHost("192.168.1.1")).toBe(true);
    expect(isBlockedHost("172.16.0.1")).toBe(true);
  });
  it("blocks link-local and metadata hostname", () => {
    expect(isBlockedHost("169.254.10.10")).toBe(true);
    expect(isBlockedHost("metadata.google.internal")).toBe(true);
  });
  it("allows public hosts", () => {
    expect(isBlockedHost("example.com")).toBe(false);
    expect(isBlockedHost("93.184.216.34")).toBe(false);
    expect(isBlockedHost("8.8.8.8")).toBe(false);
  });
  it("blocks alternate encodings of loopback/private IPs", () => {
    expect(isBlockedHost("2130706433")).toBe(true);      // decimal 127.0.0.1
    expect(isBlockedHost("0x7f000001")).toBe(true);      // hex 127.0.0.1
    expect(isBlockedHost("0177.0.0.1")).toBe(true);      // octal-ish loopback
    expect(isBlockedHost("::ffff:127.0.0.1")).toBe(true);// IPv4-mapped IPv6
    expect(isBlockedHost("::ffff:7f00:1")).toBe(true);   // IPv4-mapped IPv6 hex form
    expect(isBlockedHost("3232235521")).toBe(true);      // decimal 192.168.0.1
  });
  it("still allows public hosts in numeric form", () => {
    expect(isBlockedHost("134744072")).toBe(false);      // decimal 8.8.8.8
  });
  it("allows public hostnames that merely start with fc/fd/fe80", () => {
    expect(isBlockedHost("fc2.com")).toBe(false);
    expect(isBlockedHost("fdn.org")).toBe(false);
    expect(isBlockedHost("fe80shop.com")).toBe(false);
  });
  it("blocks the unspecified IPv6 address", () => {
    expect(isBlockedHost("::")).toBe(true);
  });
  it("has correct 172.16/12 boundaries", () => {
    expect(isBlockedHost("172.15.0.1")).toBe(false);
    expect(isBlockedHost("172.16.0.1")).toBe(true);
    expect(isBlockedHost("172.31.255.255")).toBe(true);
    expect(isBlockedHost("172.32.0.1")).toBe(false);
  });
});
