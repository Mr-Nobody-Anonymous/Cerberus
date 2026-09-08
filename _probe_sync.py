"""Sync probe test - isolate asyncio vs subprocess behavior."""
import json
import subprocess
import sys
import time

payload = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
               "clientInfo": {"name": "t", "version": "1"}},
})

proc = subprocess.Popen(
    ["python", "hexstrike_mcp.py"],
    cwd=r"c:\Users\hp\Desktop\Cerberus\adapters\hexstrike",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
t0 = time.time()
proc.stdin.write(payload + "\n")
proc.stdin.flush()
line = proc.stdout.readline()
print(f"ELAPSED: {time.time()-t0:.2f}s")
print("RESPONSE:", line[:200])
proc.kill()
