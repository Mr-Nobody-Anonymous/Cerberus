"""Quick probe test for MCP stdio servers."""
import asyncio
import json
import sys


async def probe(cwd, *cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "t", "version": "1"}},
    })
    proc.stdin.write(payload.encode() + b"\n")
    await proc.stdin.drain()
    proc.stdin.close()  # EOF — some servers wait for stdin close
    try:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=8)
        print("RESPONSE:", line.decode(errors="ignore")[:200])
    except asyncio.TimeoutError:
        print("TIMEOUT waiting for response")
    proc.kill()


async def main():
    ws = r"c:\Users\hp\Desktop\Cerberus\adapters\hexstrike"
    await probe(ws, "python", "hexstrike_mcp.py")

asyncio.run(main())
