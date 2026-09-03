"""Byte-level forensics for the doctor.py stray-token corruption (Phase A step 1)."""
import pathlib
import subprocess
import sys

DOCTOR = "cyberai/orchestrator/cli/doctor.py"


def git(*args):
    return subprocess.run(
        ["git", "--no-pager", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def show_bytes(rev, out):
    r = git("show", f"{rev}:{DOCTOR}")
    data = r.stdout
    first = data.split("\n", 1)[0]
    out.append(f"{rev}: first-line repr={first!r}")
    out.append(f"{rev}: first 12 chars={[c for c in data[:12]]}")
    bare = [c for c in data[:12] if c not in "\r\n"]
    out.append(f"{rev}: first 12 non-eol chars={bare!r}")


def main():
    out = []

    # Worktree file
    wt = pathlib.Path(DOCTOR).read_bytes()
    out.append(f"worktree: first 12 bytes={wt[:12]!r}")

    for rev in ("HEAD", "6bff1dc", "6bff1dc~1", "03fda45", "09224ae"):
        show_bytes(rev, out)

    # Blob objects named in the diffs
    for blob in ("145584e", "4db4634", "99e8192"):
        r = git("cat-file", "-t", blob)
        out.append(f"blob {blob}: type={r.stdout.strip()!r} err={r.stderr.strip()!r}")
        if r.stdout.strip() == "blob":
            r2 = git("cat-file", "-p", blob)
            d = r2.stdout
            out.append(f"blob {blob}: first-line repr={d.split(chr(10),1)[0]!r}")

    # Pickaxe for a line consisting of a single 'm' in doctor.py history (via
    # subprocess list args so cmd.exe cannot eat the '^' anchors).
    r = git("log", "-G", "^m$", "--oneline", "--all", "--", DOCTOR)
    out.append(f"pickaxe ^m$ oneline:\n{r.stdout}")
    # Pickaxe for the four-quote first line
    r = git("log", "-G", '^""""', "--oneline", "--all", "--", DOCTOR)
    out.append(f"pickaxe '^\"\"\"\"' oneline:\n{r.stdout}")

    # Show the exact first-hunk of commit 6bff1dc with visible whitespace
    r = git("show", "--stat", "--format=%H %s", "6bff1dc")
    out.append(f"6bff1dc stat:\n{r.stdout}")

    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
