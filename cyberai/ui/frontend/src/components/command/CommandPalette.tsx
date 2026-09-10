/**
 * Command palette (Ctrl+K) — fuzzy search over views + slash commands.
 * Selecting a command inserts it into the chat input; selecting a view
 * navigates.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "@/stores/app";
import type { ViewId } from "@/stores/app";

interface PaletteItem {
  key: string;
  label: string;
  hint: string;
  kind: "view" | "command";
  view?: ViewId;
  insert?: string; // text to insert into chat input
}

const VIEWS: Array<{ id: ViewId; label: string }> = [
  { id: "chat", label: "Chat" },
  { id: "dashboard", label: "Dashboard" },
  { id: "missions", label: "Missions" },
  { id: "findings", label: "Findings" },
  { id: "targets", label: "Targets" },
  { id: "agents", label: "Agents" },
  { id: "tools", label: "Tools" },
  { id: "models", label: "Models" },
  { id: "security", label: "Security" },
  { id: "memory", label: "Memory" },
  { id: "evidence", label: "Evidence" },
  { id: "sessions", label: "Sessions" },
  { id: "workspace", label: "Workspace" },
  { id: "events", label: "Events" },
];

/** Simple subsequence fuzzy match with score. */
function fuzzyScore(query: string, text: string): number {
  if (!query) return 1;
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  let qi = 0, score = 0, streak = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) {
      qi++;
      streak++;
      score += 1 + streak * 0.5; // reward consecutive hits
    } else {
      streak = 0;
    }
  }
  return qi === q.length ? score : 0;
}

export function CommandPalette() {
  const { state, dispatch } = useApp();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (state.paletteOpen) {
      setQuery(state.paletteQuery);
      setSelected(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [state.paletteOpen, state.paletteQuery]);

  const items = useMemo<PaletteItem[]>(() => {
    const viewItems: PaletteItem[] = VIEWS.map((v) => ({
      key: `view:${v.id}`, label: `Go to ${v.label}`,
      hint: "view", kind: "view", view: v.id,
    }));
    const cmdItems: PaletteItem[] = state.commands.map((c) => ({
      key: `cmd:${c.name}`, label: `/${c.name}`,
      hint: c.description, kind: "command", insert: `/${c.name} `,
    }));
    return [...viewItems, ...cmdItems];
  }, [state.commands]);

  const filtered = useMemo(() => {
    const scored = items
      .map((it) => ({ it, s: fuzzyScore(query, `${it.label} ${it.hint}`) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 12);
    return scored.map((x) => x.it);
  }, [items, query]);

  if (!state.paletteOpen) return null;

  const close = () => dispatch({ type: "PALETTE_OPEN", open: false });

  const choose = (item: PaletteItem) => {
    close();
    if (item.kind === "view" && item.view) {
      dispatch({ type: "SET_VIEW", view: item.view });
    } else if (item.insert) {
      // Insert into chat input: switch to chat view and prefill.
      dispatch({ type: "SET_VIEW", view: "chat" });
      window.dispatchEvent(
        new CustomEvent("cerberus:insert-input", { detail: item.insert }));
    }
  };

  return (
    <div onClick={close}
         style={{
           position: "fixed", inset: 0, zIndex: 100,
           background: "rgba(0,0,0,0.5)",
           display: "flex", justifyContent: "center",
           paddingTop: "12vh",
         }}>
      <div onClick={(e) => e.stopPropagation()}
           style={{
             width: 560, maxHeight: 420,
             background: "var(--cb-bg2)", border: "1px solid var(--cb-border-bright)",
             borderRadius: "var(--cb-radius-lg)", boxShadow: "var(--cb-shadow-overlay)",
             display: "flex", flexDirection: "column", overflow: "hidden",
           }}>
        <input
          ref={inputRef}
          value={query}
          placeholder="Type a command or search…"
          onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
          onKeyDown={(e) => {
            if (e.key === "Escape") close();
            else if (e.key === "ArrowDown") {
              e.preventDefault();
              setSelected((s) => Math.min(s + 1, filtered.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setSelected((s) => Math.max(s - 1, 0));
            } else if (e.key === "Enter" && filtered[selected]) {
              choose(filtered[selected]);
            }
          }}
          style={{
            border: "none", borderBottom: "1px solid var(--cb-border)",
            borderRadius: 0, padding: "12px 16px", fontSize: 14,
            background: "transparent",
          }}
        />
        <div style={{ overflowY: "auto", padding: 4 }}>
          {filtered.length === 0 && (
            <div className="faint" style={{ padding: "16px", textAlign: "center", fontSize: 12 }}>
              No matches
            </div>
          )}
          {filtered.map((item, i) => (
            <div key={item.key}
                 onClick={() => choose(item)}
                 onMouseEnter={() => setSelected(i)}
                 style={{
                   display: "flex", alignItems: "center", gap: 10,
                   padding: "8px 12px", borderRadius: "var(--cb-radius-sm)",
                   cursor: "pointer",
                   background: i === selected ? "var(--cb-bg3)" : "transparent",
                   color: i === selected ? "var(--cb-text)" : "var(--cb-text-dim)",
                 }}>
              <span className="mono"
                    style={{ color: item.kind === "command" ? "var(--cb-cyan)" : "var(--cb-violet)",
                             fontSize: 12, minWidth: 110 }}>
                {item.label}
              </span>
              <span className="faint" style={{ fontSize: 11.5, flex: 1,
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap" }}>
                {item.hint}
              </span>
              <span className="faint" style={{ fontSize: 10 }}>{item.kind}</span>
            </div>
          ))}
        </div>
        <div style={{
          padding: "6px 12px", borderTop: "1px solid var(--cb-border)",
          fontSize: 10.5, color: "var(--cb-text-faint)",
          display: "flex", gap: 14,
        }}>
          <span>↑↓ navigate</span><span>⏎ select</span><span>esc close</span>
        </div>
      </div>
    </div>
  );
}
