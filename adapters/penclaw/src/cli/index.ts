#!/usr/bin/env node
import { Command } from "commander";
import { runScanCommand } from "./scan.js";
import { VERSION } from "../utils/constants.js";
import type { Severity } from "../types/index.js";

const program = new Command();

program
  .name("penclaw")
  .description("AI-powered penetration testing CLI")
  .version(VERSION);

program
  .command("scan")
  .argument("<target...>", "Filesystem path(s) or URL(s) to scan")
  .option("-o, --output <path>", "Write the report to a file")
  .option("-f, --format <format>", "Output format: markdown, json, sarif, html")
  .option("--config <path>", "Path to a PenClaw config file")
  .option("--provider <provider>", "AI provider: anthropic, openai, ollama")
  .option("--model <model>", "AI model identifier")
  .option("--dynamic", "Enable dynamic scanning", false)
  .option("--full", "Enable both static and dynamic scanning", false)
  .option("--ci", "CI mode with severity-based exit codes", false)
  .option("--fail-on <severity>", "Minimum severity to trigger non-zero exit in CI mode", "high")
  .option("--insecure", "Disable TLS certificate verification during crawling (DANGEROUS) (browser crawl only)", false)
  .option("--allow-private", "Allow scanning private/internal/loopback hosts", false)
  .option("--auth-bearer <token>", "Bearer token for authenticated dynamic scanning")
  .option("--auth-cookie <header>", "Cookie header value for authenticated dynamic scanning")
  .option("--auth-bearer-b <token>", "Second identity bearer token (enables two-identity IDOR confirmation)")
  .action(async (targets: string[], commandOptions: Record<string, unknown>) => {
    await runScanCommand({
      target: targets.join(" "),
      output: commandOptions.output as string | undefined,
      format: commandOptions.format as "markdown" | "json" | "sarif" | "html" | undefined,
      configPath: commandOptions.config as string | undefined,
      provider: commandOptions.provider as "anthropic" | "openai" | "ollama" | undefined,
      model: commandOptions.model as string | undefined,
      dynamic: (commandOptions.dynamic as boolean) || (commandOptions.full as boolean) || undefined,
      full: commandOptions.full as boolean | undefined,
      ci: commandOptions.ci as boolean | undefined,
      failOn: commandOptions.failOn as Severity | undefined,
      insecure: commandOptions.insecure as boolean | undefined,
      allowPrivate: commandOptions.allowPrivate as boolean | undefined,
      authBearer: commandOptions.authBearer as string | undefined,
      authCookie: commandOptions.authCookie as string | undefined,
      authBearerB: commandOptions.authBearerB as string | undefined,
    });
  });

await program.parseAsync(process.argv);
