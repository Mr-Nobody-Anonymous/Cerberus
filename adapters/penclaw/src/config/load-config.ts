import path from "node:path";
import { cosmiconfig } from "cosmiconfig";
import type { PenClawConfig } from "../types/index.js";

// SECURITY: only non-executable config formats are permitted. PenClaw is pointed
// at untrusted repositories, so we must never import()/require() a config file
// discovered in (or above) the scanned target.
const SAFE_SEARCH_PLACES = [
  "package.json",
  ".penclawrc",
  ".penclawrc.json",
  ".penclawrc.yaml",
  ".penclawrc.yml",
  ".config/penclawrc",
  ".config/penclawrc.json",
  ".config/penclawrc.yaml",
  ".config/penclawrc.yml",
];

// SECURITY: `searchPlaces` only constrains search(); it does NOT constrain
// explorer.load(). Guard load() with an allowlist so it fails closed — only
// known non-executable formats are permitted for an explicit --config. Anything
// else (including executable formats like .js/.cjs/.mjs/.ts) is refused.
const SAFE_LOAD_EXTENSIONS = new Set(["", ".json", ".yaml", ".yml"]);

export async function loadConfig(searchFrom: string, configPath?: string): Promise<PenClawConfig> {
  const explorer = cosmiconfig("penclaw", {
    searchPlaces: SAFE_SEARCH_PLACES,
    // Do NOT register loaders for .js/.cjs/.mjs/.ts — cosmiconfig will not run
    // an executable config because those extensions are not in searchPlaces.
  });

  let result;
  if (configPath) {
    const resolved = path.resolve(searchFrom, configPath);
    const ext = path.extname(resolved).toLowerCase();
    const base = path.basename(resolved);
    const isRcFile = base === ".penclawrc" || base === "penclawrc";
    if (!SAFE_LOAD_EXTENSIONS.has(ext) && !isRcFile) {
      throw new Error(
        `Refusing to load config '${configPath}': only .json/.yaml/.yml or an extension-less .penclawrc are permitted (executable formats are blocked for security).`,
      );
    }
    result = await explorer.load(resolved);
  } else {
    result = await explorer.search(searchFrom);
  }

  return (result?.config as PenClawConfig | undefined) ?? {};
}
