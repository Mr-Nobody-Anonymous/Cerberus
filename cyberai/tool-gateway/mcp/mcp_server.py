"""
MCP Gateway for the Cyber AI Orchestrator.

Connects to MCP servers provided by integrated tools (HexStrike, MCPStrike,
Dark-Moon, etc.) and exposes them through a unified MCP interface.

Uses the FastMCP library when available, otherwise provides a stub
implementation that can be extended.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.config import WORKSPACE_ROOT

logger = logging.getLogger(__name__)


def _resolve_python(command: str) -> str:
    """Resolve a bare 'python' command to the current interpreter.

    Config files say "python", but the subprocess must run under the SAME
    interpreter as the CLI (e.g. the project venv) so that venv-installed
    dependencies (fastmcp, docker, ...) are importable by MCP servers.
    """
    if command in ("python", "python3", "py"):
        return sys.executable
    return command

# Line limit for subprocess stdout readers. MCP servers can emit very large
# single-line JSON responses (hexstrike's tools/list is >64KB), and the
# asyncio StreamReader default is 64KB — raise it to 8MB.
_STREAM_LIMIT = 8 * 1024 * 1024

# Environment for spawned MCP servers: force UTF-8 stdio so servers that
# print emoji banners (mcpstrike) don't crash on Windows cp1252 consoles.
_MCP_ENV = {**dict(__import__("os").environ),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1"}


class MCPGateway:
    """
    Manages MCP server connections and tool discovery.

    Discovers MCP servers from:
    - Configured MCP server definitions
    - Integrated adapters (hexstrike, mcpstrike, darkmoon)
    - Custom MCP configurations
    """

    def __init__(self, config_path: Optional[Path] = None):
        # Intentionally package-relative: mcp_config.json is default package
        # data that ships next to this module — NOT a workspace resource (do
        # not route through cyberai.config.resolve_path).
        self.config_path = config_path or Path(__file__).parent / "mcp_config.json"
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load MCP server configuration."""
        if self.config_path.exists():
            import json
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                self._servers = data.get("mcp_servers", {})
                # Resolve ADAPTERS_DIR / WORKSPACE_ROOT placeholders in cwd
                for cfg in self._servers.values():
                    if isinstance(cfg.get("cwd"), str):
                        cfg["cwd"] = cfg["cwd"].replace(
                            "ADAPTERS_DIR", str(WORKSPACE_ROOT / "adapters"))
                        cfg["cwd"] = cfg["cwd"].replace(
                            "WORKSPACE_ROOT", str(WORKSPACE_ROOT))
                logger.info(f"Loaded {len(self._servers)} MCP server configurations")
            except Exception as e:
                logger.warning(f"Failed to load MCP config: {e}")
        else:
            logger.info("No MCP config file found - using defaults")

    def discover_mcp_servers(self) -> List[Dict[str, Any]]:
        """
        Discover available MCP servers from adapters.

        Checks each adapter directory for MCP server configurations
        and returns a list of discovered servers.
        """
        discovered = []

        adapter_dirs = {
            "hexstrike": {
                "name": "hexstrike-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["hexstrike_mcp.py"],
                "cwd": str(WORKSPACE_ROOT / "adapters" / "hexstrike"),
                "capabilities": ["tool_execution", "mcp_servers"],
            },
            "mcpstrike": {
                "name": "mcpstrike-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["-m", "mcpstrike.server"],
                "cwd": str(WORKSPACE_ROOT / "adapters" / "mcpstrike"),
                "capabilities": ["tool_execution", "mcp_servers"],
            },
            "darkmoon": {
                "name": "darkmoon-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["-m", "src.server"],
                "cwd": str(WORKSPACE_ROOT / "adapters" / "darkmoon" / "mcp"),
                "capabilities": ["research", "analysis"],
            },
        }

        for name, config in adapter_dirs.items():
            adapter_path = Path(config["cwd"])
            if adapter_path.exists():
                # Check if the entry point exists
                entry = adapter_path / config["args"][-1]
                if entry.exists() or (len(config["args"]) > 1 and (adapter_path / config["args"][1]).exists()):
                    discovered.append(config)
                    self._servers[config["name"]] = config

        return discovered

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all configured MCP servers.

        Performs a REAL probe: launches each stdio server and sends a
        JSON-RPC `initialize` request. Servers that respond within the
        timeout are HEALTHY; launch failures are OFFLINE; timeouts are
        DEGRADED. Purely file-based discovery results are DISCOVERED.
        """
        results: Dict[str, Dict[str, Any]] = {}
        for name, config in self._servers.items():
            # Darkmoon has a slow startup (imports + banner + health check)
            probe_timeout = 90.0 if name == "darkmoon-mcp" else 45.0
            results[name] = await self._probe_server(name, config, timeout=probe_timeout)
        # Also include discovered servers not already probed
        for server in self.discover_mcp_servers():
            if server["name"] not in results:
                results[server["name"]] = {
                    "status": "DISCOVERED",
                    "message": f"Found at {server['cwd']} (not configured)",
                }
        return results

    async def _probe_server(self, name: str, cfg: Dict[str, Any],
                            timeout: float = 45.0) -> Dict[str, Any]:
        """Launch a stdio MCP server and send a JSON-RPC initialize probe.

        Reads the response line-by-line (stdio MCP servers stay alive
        after responding, so we must not wait for process exit).
        Note: heavy servers (e.g. hexstrike) can take 25-30s of import
        time before answering, so the default timeout is generous.
        """
        if cfg.get("type") != "stdio":
            return {"status": "NOT_TESTED",
                    "message": f"unsupported transport: {cfg.get('type')}"}
        command = cfg.get("command")
        args = list(cfg.get("args", []))
        cwd = cfg.get("cwd")
        if not command:
            return {"status": "OFFLINE", "message": "config missing command"}

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cerberus-probe", "version": "1.0"},
            },
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                _resolve_python(command), *args, cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=_STREAM_LIMIT,
                env=_MCP_ENV,
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            return {"status": "OFFLINE", "message": f"cannot launch: {e}"}

        try:
            proc.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
            await proc.stdin.drain()

            response = await asyncio.wait_for(
                _read_json_line(proc.stdout), timeout=timeout)
        except asyncio.TimeoutError:
            return {"status": "DEGRADED",
                    "message": f"no response to initialize within {timeout}s"}
        except (OSError, ValueError) as e:
            return {"status": "OFFLINE", "message": f"probe failed: {e}"}
        finally:
            await _kill_proc(proc)

        if response is None:
            err = await _read_tail(proc.stderr)
            return {"status": "OFFLINE",
                    "message": f"no JSON response {err[:150]}"}
        if "error" in response and response.get("id") == 1:
            return {"status": "HEALTHY",
                    "message": f"responded (protocol error: {response['error']})"}
        if "result" in response:
            return {"status": "HEALTHY",
                    "message": "responded to MCP initialize",
                    "details": {"serverInfo": (response.get("result") or {})
                               .get("serverInfo", {})}}
        return {"status": "DEGRADED",
                "message": f"unexpected response: {str(response)[:150]}"}

    async def list_server_tools(self, server: str,
                                timeout: float = 60.0) -> Dict[str, Any]:
        """Ask an MCP server for its tool list (JSON-RPC tools/list).

        Performs the full handshake: initialize → initialized → tools/list.
        Returns a dict with status + tools array. Never raises.
        Note: heavy servers can take 25-30s of import time before the
        initialize response, so the default timeout is generous.
        """
        cfg = self._servers.get(server)
        if cfg is None:
            for s in self.discover_mcp_servers():
                if s.get("name") == server:
                    cfg = s
                    break
        if cfg is None:
            return {"status": "ERROR", "server": server,
                    "error": f"unknown MCP server: {server}"}
        if cfg.get("type") != "stdio":
            return {"status": "ERROR", "server": server,
                    "error": f"unsupported transport: {cfg.get('type')}"}

        command = cfg.get("command")
        args = list(cfg.get("args", []))
        cwd = cfg.get("cwd")
        if not command:
            return {"status": "ERROR", "server": server,
                    "error": "server config missing command"}

        try:
            proc = await asyncio.create_subprocess_exec(
                _resolve_python(command), *args, cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=_STREAM_LIMIT,
                env=_MCP_ENV,
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            return {"status": "UNAVAILABLE", "server": server,
                    "error": f"cannot launch '{command}': {e}"}

        tools: List[Dict[str, Any]] = []
        try:
            # 1. initialize
            proc.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "cerberus", "version": "1.0"}},
            }).encode("utf-8") + b"\n")
            await proc.stdin.drain()
            init_resp = await asyncio.wait_for(
                _read_json_line(proc.stdout), timeout=timeout)
            if init_resp is None:
                err = await _read_tail(proc.stderr)
                return {"status": "ERROR", "server": server,
                        "error": f"no initialize response {err[:150]}"}

            # 2. initialized notification
            proc.stdin.write(json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }).encode("utf-8") + b"\n")
            # 3. tools/list
            proc.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            }).encode("utf-8") + b"\n")
            await proc.stdin.drain()

            # 4. read responses until we see id==2
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                msg = await asyncio.wait_for(
                    _read_json_line(proc.stdout), timeout=max(remaining, 0.1))
                if msg is None:
                    break
                if msg.get("id") == 2:
                    result = msg.get("result") or {}
                    for t in result.get("tools", []):
                        tools.append({
                            "name": t.get("name", "?"),
                            "description": (t.get("description") or "")[:200],
                        })
                    break
        except asyncio.TimeoutError:
            return {"status": "TIMEOUT", "server": server,
                    "error": f"timed out after {timeout}s"}
        except (OSError, ValueError) as e:
            return {"status": "ERROR", "server": server, "error": str(e)}
        finally:
            await _kill_proc(proc)

        if tools:
            # Cache discovered tools for list_tools()
            for t in tools:
                self._tools[f"{server}:{t['name']}"] = {"server": server, **t}
            return {"status": "SUCCESS", "server": server, "tools": tools}
        return {"status": "ERROR", "server": server,
                "error": "no tools/list response"}

    def list_tools(self) -> List[str]:
        """List all tools available through MCP servers."""
        return sorted(self._tools.keys())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool info by name."""
        return self._tools.get(name)

    def list_servers(self) -> List[Dict[str, Any]]:
        """Return all known MCP server configs (configured + discovered)."""
        discovered = self.discover_mcp_servers()
        seen = set()
        out: List[Dict[str, Any]] = []
        for s in discovered + list(self._servers.values()):
            n = s.get("name", "")
            if n and n not in seen:
                seen.add(n)
                out.append(s)
        return out

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Dispatch a tool call to the named MCP server.

        Supports stdio MCP servers by spawning the configured command and
        sending a JSON-RPC `tools/call` request. If the server is not
        reachable, the gateway returns a structured error envelope
        instead of raising, so the CLI surface always reports something
        useful.
        """
        arguments = arguments or {}
        cfg = self._servers.get(server)
        if cfg is None:
            for s in self.discover_mcp_servers():
                if s.get("name") == server:
                    cfg = s
                    break
        if cfg is None:
            return {
                "status": "ERROR",
                "server": server,
                "tool": tool,
                "error": f"unknown MCP server: {server}",
            }
        if cfg.get("type") != "stdio":
            return {
                "status": "ERROR",
                "server": server,
                "tool": tool,
                "error": f"unsupported transport: {cfg.get('type')}",
            }

        command = cfg.get("command")
        args = list(cfg.get("args", []))
        cwd = cfg.get("cwd")
        if not command:
            return {
                "status": "ERROR",
                "server": server,
                "tool": tool,
                "error": "server config missing command",
            }

        # Full MCP JSON-RPC handshake: initialize → initialized → tools/call.
        # We avoid importing fastmcp here so this works in any environment.
        try:
            proc = await asyncio.create_subprocess_exec(
                _resolve_python(command),
                *args,
                cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=_STREAM_LIMIT,
                env=_MCP_ENV,
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            return {
                "status": "UNAVAILABLE",
                "server": server,
                "tool": tool,
                "error": f"cannot launch '{command}': {e}",
            }

        result: Dict[str, Any] = {}
        try:
            # 1. initialize
            proc.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "cerberus", "version": "1.0"}},
            }).encode("utf-8") + b"\n")
            await proc.stdin.drain()
            init_resp = await asyncio.wait_for(
                _read_json_line(proc.stdout), timeout=timeout)
            if init_resp is None:
                err = await _read_tail(proc.stderr)
                return {
                    "status": "ERROR", "server": server, "tool": tool,
                    "error": f"no initialize response {err[:150]}",
                }

            # 2. initialized notification + tools/call request
            proc.stdin.write(json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }).encode("utf-8") + b"\n")
            proc.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            }).encode("utf-8") + b"\n")
            await proc.stdin.drain()

            # 3. read responses until we see id==2
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                msg = await asyncio.wait_for(
                    _read_json_line(proc.stdout), timeout=max(remaining, 0.1))
                if msg is None:
                    break
                if msg.get("id") == 2:
                    result = msg
                    break
        except asyncio.TimeoutError:
            return {
                "status": "TIMEOUT", "server": server, "tool": tool,
                "error": f"timed out after {timeout}s",
            }
        except (OSError, ValueError) as e:
            return {
                "status": "ERROR", "server": server, "tool": tool,
                "error": str(e),
            }
        finally:
            await _kill_proc(proc)

        if not result:
            err = await _read_tail(proc.stderr)
            return {
                "status": "ERROR", "server": server, "tool": tool,
                "error": f"no tools/call response {err[:150]}",
            }
        if "error" in result:
            return {
                "status": "ERROR", "server": server, "tool": tool,
                "error": str(result["error"])[:400],
                "arguments": arguments,
            }
        return {
            "status": "SUCCESS",
            "server": server,
            "tool": tool,
            "arguments": arguments,
            "result": result.get("result"),
        }

    async def health(self) -> Dict[str, Any]:
        """Aggregate health across configured servers."""
        configured = list(self._servers.keys())
        discovered = [s.get("name") for s in self.discover_mcp_servers()]
        checks = await self.health_check_all()
        healthy = sum(1 for v in checks.values() if v.get("status") == "HEALTHY")
        reachable = sum(1 for v in checks.values()
                        if v.get("status") in ("HEALTHY", "DEGRADED", "DISCOVERED"))
        return {
            "configured": configured,
            "discovered": discovered,
            "checks": checks,
            "healthy": healthy,
            "reachable": reachable,
            "total": len(checks),
        }

    def register_server(self, name: str, config: Dict[str, Any]) -> None:
        """Register (or replace) an MCP server configuration at runtime."""
        config.setdefault("name", name)
        self._servers[name] = config
        logger.info(f"Registered MCP server: {name}")

    def unregister_server(self, name: str) -> bool:
        """Remove a registered MCP server. Returns True if it existed."""
        if name in self._servers:
            del self._servers[name]
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Return the MCP gateway state as a dict."""
        return {
            "servers": self._servers,
            "tools": list(self._tools.keys()),
            "config_path": str(self.config_path),
        }


# ---------------------------------------------------------------------------
# stdio helpers
# ---------------------------------------------------------------------------

async def _read_json_line(stream: asyncio.StreamReader,
                          max_lines: int = 500) -> Optional[Dict[str, Any]]:
    """Read lines from a stdio MCP server until one parses as JSON.

    Skips banner/log lines that some servers print before protocol output.
    Returns None on EOF without a JSON line.
    """
    for _ in range(max_lines):
        line = await stream.readline()
        if not line:
            return None
        text = line.decode("utf-8", errors="ignore").strip()
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue
    return None


async def _read_tail(stream: Optional[asyncio.StreamReader],
                     max_bytes: int = 400) -> str:
    """Best-effort read of remaining stderr for diagnostics."""
    if stream is None:
        return ""
    try:
        data = await asyncio.wait_for(stream.read(max_bytes), timeout=1.0)
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


async def _kill_proc(proc: Optional[asyncio.subprocess.Process]) -> None:
    """Terminate a subprocess cleanly (Windows + POSIX).

    Also closes the transport pipes so Windows proactor transports
    don't emit 'unclosed transport' ResourceWarnings at shutdown.
    """
    if proc is None:
        return
    try:
        if proc.returncode is None:
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                pass
        # Give the process a moment to die, then close pipes to avoid
        # Windows proactor 'unclosed transport' ResourceWarnings.
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass
        for pipe in (proc.stdin, proc.stdout, proc.stderr):
            if pipe is not None:
                try:
                    pipe.close()
                except Exception:
                    pass
        # Close the underlying transport so its __del__ doesn't complain
        # after the event loop is gone (Windows proactor).
        transport = getattr(proc, "_transport", None)
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass
    except Exception:
        pass
