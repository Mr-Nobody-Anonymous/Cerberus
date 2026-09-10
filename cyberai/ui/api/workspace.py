"""Workspace endpoints — read-only, strictly scoped.

    GET /api/v1/workspace/tree     directory tree (approved roots only)
    GET /api/v1/workspace/file     file content (approved roots only)

SECURITY: every path is resolved and verified to live under an approved
workspace root. Path traversal (../, absolute paths, symlinks escaping
the root, Windows drive letters) is rejected with 403.
"""

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from cyberai.config import WORKSPACE_ROOT

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace"])

# Approved roots for the file explorer (relative to WORKSPACE_ROOT).
_APPROVED_ROOTS = ("lab", "knowledge", "memory", "logs", "projects", "docs")

# Extensions safe to serve as text.
_TEXT_SUFFIXES = {
    ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".csv",
    ".log", ".xml", ".cff", ".sh", ".ps1", ".bat", ".env", ".gitignore",
    ".dockerfile", ".cff", ".rst",
}
_MAX_FILE_BYTES = 512 * 1024  # 512 KiB


def _resolve_safe(rel_path: str) -> Path:
    """Resolve rel_path under an approved root; raise 403 on escape."""
    rel_path = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if not rel_path:
        raise HTTPException(status_code=400, detail="path is required")
    first = rel_path.split("/", 1)[0]
    if first not in _APPROVED_ROOTS:
        raise HTTPException(
            status_code=403,
            detail=f"access denied: '{first}' is not an approved workspace root "
                   f"(approved: {', '.join(_APPROVED_ROOTS)})")
    candidate = (WORKSPACE_ROOT / rel_path).resolve()
    root = (WORKSPACE_ROOT / first).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403,
                            detail="access denied: path escapes the workspace root")
    # Also ensure it stays under WORKSPACE_ROOT (defense in depth).
    try:
        candidate.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=403,
                            detail="access denied: path escapes the workspace")
    return candidate


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in _TEXT_SUFFIXES or path.name.lower() in (
        "dockerfile", "makefile", "license", "readme")


@router.get("/tree")
async def workspace_tree(path: str = "", depth: int = Query(default=2, ge=0, le=4)):
    """Directory listing for the explorer pane. Approved roots only."""
    base = WORKSPACE_ROOT if not path else _resolve_safe(path)
    if path and not base.is_dir():
        raise HTTPException(status_code=404, detail="directory not found")

    def walk(dir_path: Path, remaining_depth: int) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        try:
            children = sorted(dir_path.iterdir(),
                              key=lambda p: (p.is_file(), p.name.lower()))
        except (OSError, PermissionError):
            return entries
        for child in children:
            if child.name.startswith(".") or child.name == "__pycache__":
                continue
            entry: Dict[str, Any] = {
                "name": child.name,
                "path": str(child.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                "type": "directory" if child.is_dir() else "file",
            }
            if child.is_dir() and remaining_depth > 0:
                entry["children"] = walk(child, remaining_depth - 1)
            elif child.is_file():
                try:
                    entry["size"] = child.stat().st_size
                except OSError:
                    entry["size"] = 0
            entries.append(entry)
        return entries

    if path:
        return {"path": path, "entries": walk(base, depth)}
    # Root listing: approved roots only.
    entries = [
        {"name": name, "path": name, "type": "directory",
         "children": walk(WORKSPACE_ROOT / name, depth - 1) if depth > 0 else []}
        for name in _APPROVED_ROOTS if (WORKSPACE_ROOT / name).exists()
    ]
    return {"path": "", "entries": entries}


@router.get("/file")
async def workspace_file(path: str = Query(..., description="workspace-relative path")):
    """Read one workspace file (text only, size-capped, approved roots only)."""
    target = _resolve_safe(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    if not _is_text_file(target):
        raise HTTPException(status_code=415,
                            detail=f"unsupported file type: {target.suffix or 'none'}")
    try:
        size = target.stat().st_size
    except OSError:
        raise HTTPException(status_code=404, detail="file not found")
    if size > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413,
                            detail=f"file too large ({size} bytes; max {_MAX_FILE_BYTES})")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return PlainTextResponse(content)
