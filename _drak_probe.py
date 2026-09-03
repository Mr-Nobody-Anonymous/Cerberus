"""Probe the drakben subprocess to understand the failing test."""
import asyncio
import sys

sys.path.insert(0, r"c:\Users\hp\Desktop\Cerberus")

from cyberai.security.sandbox import run_subprocess

cmd = [sys.executable, r"c:\Users\hp\Desktop\Cerberus\adapters\drakben\drakben.py", "--help"]
r = asyncio.get_event_loop().run_until_complete(
    asyncio.to_thread(run_subprocess, cmd, timeout=30, network_allowed=True,
                       cwd=r"c:\Users\hp\Desktop\Cerberus\adapters\drakben"))
out = []
out.append(f"success={r.success}")
out.append(f"returncode={r.returncode}")
out.append(f"timed_out={r.timed_out}")
out.append(f"error={r.error!r}")
out.append(f"stdout[:400]={r.stdout[:400]!r}")
out.append(f"stderr[:600]={r.stderr[:600]!r}")
with open("_drak_probe.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written")
