/**
 * Workspace — restricted file explorer (lab/, knowledge/, memory/, logs/,
 * projects/, docs/) + text file viewer. Path traversal is rejected server-side.
 */

import { useState } from "react";
import { workspaceApi } from "@/lib/api";
import type { WorkspaceEntry } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

function iconFor(entry: WorkspaceEntry) {
  if (entry.type === "directory") return "▸";
  const ext = entry.name.split(".").pop()?.toLowerCase() ?? "";
  if (["py", "js", "ts", "tsx", "sh", "ps1"].includes(ext)) return "{}";
  if (["json", "yaml", "yml", "toml"].includes(ext)) return "⚙";
  if (["md", "txt", "rst"].includes(ext)) return "≡";
  return "·";
}

function TreeRow({ entry, path, onOpen, depth }: {
  entry: WorkspaceEntry; path: string;
  onOpen: (path: string, isDir: boolean) => void; depth: number;
}) {
  const [open, setOpen] = useState(false);
  const { data, loading } = useFetch(
    () => open ? workspaceApi.tree(`${path}/${entry.name}`) : Promise.resolve(null),
    [open, path, entry.name],
  );

  return (
    <div>
      <div
        onClick={() => entry.type === "directory"
          ? setOpen((o) => !o)
          : onOpen(`${path}/${entry.name}`, false)}
        style={{
          display: "flex", gap: 8, alignItems: "center",
          padding: "3px 8px", cursor: "pointer", fontSize: 12,
          paddingLeft: 8 + depth * 14,
          borderRadius: 4,
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--cb-bg2)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        <span style={{ color: entry.type === "directory" ? "var(--cb-cyan)" : "var(--cb-text-dim)",
                       width: 14, textAlign: "center", flexShrink: 0 }}>
          {entry.type === "directory" ? (open ? "▾" : "▸") : iconFor(entry)}
        </span>
        <span style={{
          fontFamily: entry.type === "directory" ? "var(--cb-font-ui)" : "var(--cb-font-mono)",
          color: entry.type === "directory" ? "var(--cb-text)" : "var(--cb-text-dim)",
        }}>
          {entry.name}
        </span>
      </div>
      {open && entry.type === "directory" && (
        <div>
          {loading && <div className="faint" style={{ paddingLeft: 30 + depth * 14,
                                                      fontSize: 11 }}>loading…</div>}
          {(data?.entries ?? []).map((child) => (
            <TreeRow key={child.name} entry={child} path={`${path}/${entry.name}`}
                     onOpen={onOpen} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function WorkspacePage() {
  const toast = useToast();
  const [file, setFile] = useState<{ path: string; content: string } | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const { data, loading, error } = useFetch(() => workspaceApi.tree(""), []);

  const openFile = async (path: string) => {
    setFileError(null);
    try {
      const content = await workspaceApi.file(path);
      setFile({ path, content });
    } catch (e) {
      setFile(null);
      setFileError(e instanceof Error ? e.message : "cannot open file");
      toast("error", "cannot open file (binary or too large)");
    }
  };

  if (error) return <ErrorBox error={error} />;
  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const entries = data?.entries ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Workspace" subtitle="restricted roots: lab · knowledge · memory · logs · projects · docs" />
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {/* Tree */}
        <div style={{
          width: 280, flexShrink: 0, overflowY: "auto",
          borderRight: "1px solid var(--cb-border)", padding: "10px 6px",
        }}>
          {entries.length === 0 && <EmptyState icon="☰" title="Empty workspace" />}
          {entries.map((e) => (
            <TreeRow key={e.name} entry={e} path="" onOpen={(p) => void openFile(p)} depth={0} />
          ))}
        </div>

        {/* File viewer */}
        <div style={{ flex: 1, overflow: "auto", padding: "14px 18px", minWidth: 0 }}>
          {fileError && <ErrorBox error={fileError} />}
          {!file && !fileError && (
            <EmptyState icon="≡" title="Select a file"
                         hint="Browse the tree and click a text file to view it. Binary and large files are refused by the server." />
          )}
          {file && (
            <>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
                <Pill tone="info">{file.path}</Pill>
                <span className="faint" style={{ fontSize: 10.5 }}>
                  {file.content.length.toLocaleString()} chars
                </span>
              </div>
              <pre className="mono" style={{
                fontSize: 11.5, lineHeight: 1.6, whiteSpace: "pre-wrap",
                overflowWrap: "anywhere",
                background: "var(--cb-bg1)", border: "1px solid var(--cb-border)",
                borderRadius: "var(--cb-radius-md)", padding: 14,
              }}>
                {file.content}
              </pre>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
