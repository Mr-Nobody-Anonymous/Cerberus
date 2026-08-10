import { describe, it, expect, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadConfig } from "../src/config/load-config.js";

async function makeTempDir(): Promise<string> {
  return fs.mkdtemp(path.join(os.tmpdir(), "penclaw-cfg-"));
}

describe("loadConfig", () => {
  const dirs: string[] = [];
  afterEach(async () => {
    for (const d of dirs) await fs.rm(d, { recursive: true, force: true });
    dirs.length = 0;
  });

  it("does NOT execute a malicious .penclawrc.js in the searched dir", async () => {
    const dir = await makeTempDir();
    dirs.push(dir);
    await fs.writeFile(
      path.join(dir, ".penclawrc.js"),
      "throw new Error('RCE: config code executed');\n",
    );
    const config = await loadConfig(dir, undefined);
    expect(config).toEqual({});
  });

  it("still loads a .penclawrc.yml", async () => {
    const dir = await makeTempDir();
    dirs.push(dir);
    await fs.writeFile(path.join(dir, ".penclawrc.yml"), "ai:\n  provider: openai\n");
    const config = await loadConfig(dir, undefined);
    expect(config.ai?.provider).toBe("openai");
  });

  it("refuses to execute a .js file passed via explicit configPath", async () => {
    const dir = await makeTempDir();
    dirs.push(dir);
    await fs.writeFile(
      path.join(dir, "evil.js"),
      "throw new Error('RCE via --config');\n",
    );
    // Must not execute the file. It must NOT throw the 'RCE via --config' message
    // from inside the file; it must throw a clear "not permitted" error instead.
    await expect(loadConfig(dir, "evil.js")).rejects.toThrow(/unsupported|not permitted|executable/i);
  });

  it("loads a .penclawrc.json", async () => {
    const dir = await makeTempDir();
    dirs.push(dir);
    await fs.writeFile(path.join(dir, ".penclawrc.json"), JSON.stringify({ ai: { provider: "ollama" } }));
    const config = await loadConfig(dir, undefined);
    expect(config.ai?.provider).toBe("ollama");
  });

  it("loads an explicit .json config via configPath", async () => {
    const dir = await makeTempDir();
    dirs.push(dir);
    await fs.writeFile(path.join(dir, "custom.json"), JSON.stringify({ ai: { provider: "openai" } }));
    const config = await loadConfig(dir, "custom.json");
    expect(config.ai?.provider).toBe("openai");
  });
});
