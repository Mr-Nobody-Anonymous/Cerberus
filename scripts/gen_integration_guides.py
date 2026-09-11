"""One-off generator: rewrite the 17 per-adapter INTEGRATION.md guides
with accurate, adapter-specific content (contract, capabilities, health
prerequisites, real run instructions, vendored-copy update procedure).

Run from the repository root:
    python scripts/gen_integration_guides.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = ROOT / "adapters"

# registry_name -> guide data
DATA = {
    "pentagi": dict(
        dirname="pentagi", orig="PentAGI",
        repo="https://github.com/vxcontrol/pentagi",
        lic="See LICENSE file in repository",
        role="Primary autonomous pentesting agent (research, analysis, exploitation, reporting)",
        method="REST/GraphQL API served by its Docker Compose stack",
        module="adapters.pentagi", upstream_sub="pentagi tree at the adapter root",
        caps=[("research", "Research via PentAGI agent"),
              ("analysis", "Analyze target findings"),
              ("exploitation", "Exploit weaknesses (authorized lab only)"),
              ("reporting", "Generate assessment report")],
        health=["Docker installed and the PentAGI compose stack running (`docker compose up -d`)",
                "API port listening (default `https://localhost:8443`; override with `PENTAGI_API_URL`)",
                "UNAVAILABLE/WARN otherwise — WARN includes the exact start command"],
        run=["cd adapters/pentagi",
             "cp .env.example .env   # configure LLM providers",
             "docker compose up -d",
             "# API at https://localhost:8443 (self-signed cert)"],
    ),
    "strix": dict(
        dirname="strix", orig="Strix",
        repo="https://github.com/usestrix/strix",
        lic="Apache-2.0",
        role="Autonomous pentest agent (recon, scanning, analysis, exploitation)",
        method="CLI invocation of `strix/interface/main.py` in the sandbox",
        module="adapters.strix", upstream_sub="strix/",
        caps=[("recon", "Recon via Strix agent"),
              ("scan", "Vulnerability scan via Strix agent"),
              ("analysis", "Analyze findings via Strix agent"),
              ("exploitation", "Exploit via Strix agent (authorized lab only)")],
        health=["Python interpreter available",
                "`strix/interface/main.py` present",
                "Docker installed for real scans (the Strix sandbox image) — without it the adapter reports WARN"],
        run=["# Real scans need Docker + a configured LLM:",
             "cd adapters/strix",
             "python -m strix.interface.main --help   # importability probe",
             "# full usage: see the upstream README.md in this directory"],
    ),
    "hexstrike": dict(
        dirname="hexstrike", orig="HexStrike AI",
        repo="https://github.com/0x4m4/hexstrike-ai",
        lic="MIT",
        role="Tool gateway exposing 150+ offensive security tools via REST/MCP",
        method="Flask REST API + MCP (default port 8000)",
        module="adapters.hexstrike", upstream_sub="hexstrike tree at the adapter root",
        caps=[("tool_execution", "Execute security tools via HexStrike REST"),
              ("mcp_servers", "Drive HexStrike MCP servers"),
              ("web_scraping", "Web scraping via HexStrike browser agent")],
        health=["HexStrike server listening (default `http://localhost:8000`; override with `HEXSTRIKE_API_URL`)"],
        run=["python adapters/hexstrike/hexstrike_server.py",
             "# configure API keys for the tools you want to drive"],
    ),
    "mcpstrike": dict(
        dirname="mcpstrike", orig="mcpstrike",
        repo="https://github.com/ente0/mcpstrike",
        lic="MIT",
        role="Ollama-driven MCP tool gateway",
        method="FastAPI server + MCP (default port 8080)",
        module="adapters.mcpstrike", upstream_sub="src/",
        caps=[("tool_execution", "Execute security tools via mcpstrike"),
              ("mcp_servers", "Drive mcpstrike MCP servers")],
        health=["mcpstrike server listening (default `http://localhost:8080`; override with `MCPSTRIKE_API_URL`)"],
        run=["cd adapters/mcpstrike/src",
             "python -m mcpstrike.server.app   # needs a local Ollama daemon"],
    ),
    "darkmoon": dict(
        dirname="darkmoon", orig="Dark-Moon",
        repo="https://github.com/ASCIT31/Dark-Moon",
        lic="GPL v3",
        role="Autonomous pentesting agent (research, analysis, exploitation)",
        method="MCP over HTTP (default port 8000)",
        module="adapters.darkmoon", upstream_sub="mcp/",
        caps=[("research", "Research via Dark-Moon agent"),
              ("analysis", "Analyze target findings"),
              ("exploitation", "Exploit weaknesses (authorized lab only)")],
        health=["Dark-Moon MCP server listening (default `http://localhost:8000`; override with `DARKMOON_API_URL`)"],
        run=["python adapters/darkmoon/mcp/src/server.py"],
    ),
    "cai": dict(
        dirname="cai", orig="Cybersecurity AI (CAI)",
        repo="https://github.com/aliasrobotics/CAI",
        lic="Dual MIT + Proprietary (see upstream LICENSE)",
        role="Agent framework for cybersecurity research and analysis",
        method="Python library imported in-process (vendored source preferred)",
        module="adapters.cai", upstream_sub="cai tree at the adapter root",
        caps=[("research", "Research via CAI agents"),
              ("analysis", "Analyze via CAI agents"),
              ("agent_framework", "Run CAI agent framework")],
        health=["CAI importable in the current interpreter",
                "If not installed: `pip install -e adapters/cai` (the adapter also inserts the vendored source on sys.path)"],
        run=["pip install -e adapters/cai",
             "# then the orchestrator can drive CAI agents in-process"],
    ),
    "pentestgpt": dict(
        dirname="pentestgpt", orig="PentestGPT",
        repo="https://github.com/greydgl/pentestgpt",
        lic="MIT",
        role="GPT-driven pentest planning and research assistant",
        method="CLI invocation of `pentestgpt_legacy/main.py` in the sandbox",
        module="adapters.pentestgpt", upstream_sub="pentestgpt_legacy/",
        caps=[("research", "Research via PentestGPT"),
              ("planning", "Plan attack paths via PentestGPT")],
        health=["Python interpreter available",
                "`pentestgpt_legacy/main.py` present"],
        run=["cd adapters/pentestgpt",
             "python pentestgpt_legacy/main.py   # interactive; needs an OpenAI API key"],
    ),
    "pentestagent": dict(
        dirname="pentestagent", orig="PentestAgent",
        repo="https://github.com/GH05TCREW/pentestagent",
        lic="MIT",
        role="Autonomous pentesting agent (research, analysis, exploitation)",
        method="CLI invocation of `pentestagent/interface/main.py` in the sandbox",
        module="adapters.pentestagent", upstream_sub="pentestagent/",
        caps=[("research", "Research via PentestAgent"),
              ("analysis", "Analyze findings via PentestAgent"),
              ("exploitation", "Exploit via PentestAgent (authorized lab only)")],
        health=["Python interpreter available",
                "`pentestagent/interface/main.py` present"],
        run=["cd adapters/pentestagent",
             "python pentestagent/interface/main.py --help"],
    ),
    "cyberstrikeai": dict(
        dirname="cyberstrikeai", orig="CyberStrikeAI",
        repo="https://github.com/Ed1s0nZ/CyberStrikeAI",
        lic="See LICENSE",
        role="MCP-driven security tool executor with analysis",
        method="Gin (Go) REST API + MCP (default port 8080)",
        module="adapters.cyberstrikeai", upstream_sub="Go sources at the adapter root",
        caps=[("tool_execution", "Execute security tools via CyberStrikeAI"),
              ("mcp_servers", "Drive CyberStrikeAI MCP servers"),
              ("analysis", "Analyze target findings")],
        health=["CyberStrikeAI Go server listening (default `http://localhost:8080`; override with `CYBERSTRIKEAI_API_URL`)"],
        run=["cd adapters/cyberstrikeai",
             "go build ./cmd/...   # then start the server (see upstream README)"],
    ),
    "autopentest": dict(
        dirname="autopentest", orig="AutoPentest",
        repo="https://github.com/JuliusHenke/autopentest",
        lic="See LICENSE.md",
        role="ML-driven attack-path planning and research",
        method="CLI invocation of `src/main.py` in the sandbox",
        module="adapters.autopentest", upstream_sub="src/",
        caps=[("research", "Research via AutoPentest"),
              ("planning", "Plan attack paths via AutoPentest")],
        health=["Python interpreter available",
                "`src/main.py` present"],
        run=["cd adapters/autopentest",
             "python src/main.py --help"],
    ),
    "penclaw": dict(
        dirname="penclaw", orig="PenClaw",
        repo="https://github.com/andupetcu/penclaw",
        lic="See LICENSE",
        role="Code security analysis (static, dynamic, secret detection)",
        method="Node.js CLI (`dist/cli/index.js`) run in the sandbox",
        module="adapters.penclaw", upstream_sub="src/ (built to dist/)",
        caps=[("static_analysis", "Static analysis via PenClaw"),
              ("dynamic_scanning", "Dynamic scanning via PenClaw"),
              ("secret_detection", "Secret detection via PenClaw")],
        health=["Node.js installed",
                "`dist/cli/index.js` built — otherwise run `npm install && npm run build`"],
        run=["cd adapters/penclaw",
             "npm install && npm run build",
             "node dist/cli/index.js --help"],
    ),
    "luan1aoagent": dict(
        dirname="luan1aoagent", orig="LuaN1aoAgent",
        repo="https://github.com/SanMuzZzZz/LuaN1aoAgent",
        lic="AGPL v3",
        role="Autonomous security agent (research, analysis, planning)",
        method="Node.js CLI (`dist/cli.js`) run in the sandbox",
        module="adapters.luan1aoagent", upstream_sub="TypeScript sources (built to dist/)",
        caps=[("research", "Research via LuaN1aoAgent"),
              ("analysis", "Analyze via LuaN1aoAgent"),
              ("planning", "Plan via LuaN1aoAgent")],
        health=["Node.js installed",
                "`dist/cli.js` built — otherwise run `npm install && npm run build`"],
        run=["cd adapters/luan1aoagent",
             "npm install && npm run build",
             "node dist/cli.js --help"],
    ),
    "aracne": dict(
        dirname="aracne", orig="ARACNE",
        repo="https://github.com/stratosphereips/aracne",
        lic="See LICENSE",
        role="SSH-driven exploitation and research agent",
        method="CLI invocation of `aracne.py` in the sandbox",
        module="adapters.aracne", upstream_sub="aracne.py at the adapter root",
        caps=[("research", "Research via ARACNE"),
              ("exploitation", "Exploit via ARACNE (authorized lab only)"),
              ("ssh_driven", "SSH-driven execution via ARACNE")],
        health=["Python interpreter available",
                "`aracne.py` present"],
        run=["cd adapters/aracne",
             "python aracne.py --help"],
    ),
    "guardian_cli": dict(
        dirname="guardian-cli", orig="Guardian",
        repo="https://github.com/zakirkun/guardian-cli",
        lic="MIT",
        role="Recon/scan/analysis/report security CLI",
        method="CLI (`python -m cli.main`) run in the sandbox",
        module="adapters.guardian-cli", upstream_sub="cli/",
        caps=[("recon", "Network recon via Guardian scan"),
              ("scan", "Port scan via Guardian scan"),
              ("analysis", "Analyze via Guardian analyze"),
              ("report", "Report via Guardian report")],
        health=["`cli/main.py` present"],
        run=["cd adapters/guardian-cli",
             "python -m cli.main --help"],
        note=("The directory is dash-named; the orchestrator resolves it via the "
              "`_HyphenAdapterFinder` in `adapters/__init__.py` (registry key: "
              "`guardian_cli`, module string: `adapters.guardian-cli`)."),
    ),
    "drakben": dict(
        dirname="drakben", orig="DRAKBEN",
        repo="https://github.com/ahmetdrak/drakben",
        lic="MIT",
        role="Autonomous pentesting agent (recon, analysis, exploitation)",
        method="CLI invocation of `drakben.py` in the sandbox",
        module="adapters.drakben", upstream_sub="drakben.py + core/",
        caps=[("recon", "Network recon via DRAKBEN tools"),
              ("analysis", "Analyze target findings"),
              ("exploitation", "Exploit weaknesses")],
        health=["Python interpreter available",
                "`drakben.py` present",
                "`core/` package present"],
        run=["cd adapters/drakben",
             "python drakben.py --help"],
    ),
    "kali_pentest": dict(
        dirname="kali-pentest", orig="kali-pentest",
        repo="https://github.com/x-glacier/kali-pentest",
        lic="See LICENSE",
        role="Kali tool methodology knowledge base (searchable reference)",
        method="Documentation search over the vendored guides",
        module="adapters.kali-pentest", upstream_sub="kali-pentest/",
        caps=[("research", "Query penetration testing tool methodology and commands"),
              ("documentation", "Kali Linux tool usage syntax and attack workflows")],
        health=["Adapter directory present",
                "`README.md` present (the searchable index)"],
        run=["# No service to start — the adapter searches the vendored guides:",
             "ls adapters/kali-pentest/kali-pentest"],
        note=("The directory is dash-named; the orchestrator resolves it via the "
              "`_HyphenAdapterFinder` in `adapters/__init__.py` (registry key: "
              "`kali_pentest`, module string: `adapters.kali-pentest`)."),
    ),
    "h4cker": dict(
        dirname="h4cker", orig="h4cker",
        repo="https://github.com/The-Art-of-Hacking/h4cker",
        lic="See LICENSE",
        role="Security training/research knowledge base (searchable reference)",
        method="Documentation search over the vendored tree",
        module="adapters.h4cker", upstream_sub="h4cker tree at the adapter root",
        caps=[("research", "Query CVEs, CWEs, and vulnerability research topics"),
              ("documentation", "Query security training and methodology references")],
        health=["Adapter directory present",
                "`README.md` present (the searchable index)"],
        run=["# No service to start — the adapter searches the vendored tree:",
             "ls adapters/h4cker"],
    ),
}

TEMPLATE = """# Integration Record — {orig}

## Original Project
- **Name:** {orig}
- **Repository:** {repo}
- **License:** {lic}
- **Vendored as:** `adapters/{dirname}/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** {role}
- **Integration Method:** {method}
- **Adapter Module:** `{module}` (registry key: `{key}`)
- **Adapter Base:** `SandboxedAdapter` — policy-gated, evidence-logged

## Adapter Contract
Implements the standard orchestrator adapter interface
(`cyberai/orchestrator/adapters/base.py`):

- `health_check()` → `{{status, message, details}}`; status is one of
  `AVAILABLE`, `WARN`, `UNAVAILABLE`, `ERROR`
- `capabilities()` → list of `AdapterCapability(name, description)`
- `execute(task)` → `AdapterResult(success, output, error, evidence, metadata)`.
  `execute()` is the only public entry point: it authorizes the target with
  the policy engine (fails closed) and records evidence before delegating
  to `_do_execute()`. Never call `_do_execute()` directly.
- Task shape: `{{action, target: {{id, host, environment, allowed}}, parameters, session_id}}`

## Capabilities
{caps}

## Health Check Prerequisites
{health}

## How To Run
```
{run}
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/{dirname}                     # Windows: Remove-Item -Recurse adapters\\{dirname}
git clone {repo} adapters/{dirname}
```
The Cerberus adapter wrapper lives in `adapters/{dirname}/__init__.py`;
the upstream tree starts at `adapters/{dirname}/{upstream_sub}`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/{dirname}/__init__.py`)
after re-cloning.

{note}
## Attribution
- **Original Repository:** {repo}
- **License:** {lic}
"""


def main():
    written = []
    for key, d in DATA.items():
        caps = "\n".join(
            f"- `{name}` — {desc}" for name, desc in d["caps"])
        health = "\n".join(f"- {h}" for h in d["health"])
        run = "\n".join(d["run"])
        note = (d.get("note") + "\n\n") if d.get("note") else ""
        content = TEMPLATE.format(
            orig=d["orig"], repo=d["repo"], lic=d["lic"],
            dirname=d["dirname"], role=d["role"], method=d["method"],
            module=d["module"], key=key, caps=caps, health=health,
            run=run, upstream_sub=d["upstream_sub"], note=note,
        )
        # collapse any accidental double blank lines
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")
        path = ADAPTERS / d["dirname"] / "INTEGRATION.md"
        path.write_text(content, encoding="utf-8")
        written.append(f"{key}: {len(content.splitlines())} lines")
    print("\n".join(written))
    print(f"OK — {len(written)} guides regenerated")


if __name__ == "__main__":
    main()
