/**
 * Chat input — textarea with slash-command autocomplete popup,
 * Enter to send, Shift+Enter for newline. Listens for the
 * 'cerberus:insert-input' event from the command palette.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "@/stores/app";

export function ChatInput({ onSend, disabled }: {
  onSend: (text: string) => void; disabled?: boolean;
}) {
  const { state } = useApp();
  const [text, setText] = useState("");
  const [sel, setSel] = useState(0);
  const ref = useRef<HTMLTextAreaElement>(null);

  // Palette inserts (e.g. choosing /findings from Ctrl+K).
  useEffect(() => {
    const onInsert = (e: Event) => {
      const detail = (e as CustomEvent<string>).detail;
      setText((t) => (t ? `${t} ${detail}` : detail));
      ref.current?.focus();
    };
    window.addEventListener("cerberus:insert-input", onInsert);
    return () => window.removeEventListener("cerberus:insert-input", onInsert);
  }, []);

  // Slash-command autocomplete: "/sta" → [status, ...]
  const slash = text.startsWith("/") ? text.slice(1).split(" ")[0] : "";
  const matches = useMemo(() => {
    if (!slash) return [];
    return state.commands
      .filter((c) => c.name.startsWith(slash.toLowerCase()))
      .slice(0, 8);
  }, [slash, state.commands]);

  useEffect(() => setSel(0), [matches.length]);

  const send = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
  };

  const complete = (name: string) => {
    const rest = text.slice(1).split(" ").slice(1).join(" ");
    setText(`/${name}${rest ? ` ${rest}` : " "}`);
    ref.current?.focus();
  };

  return (
    <div style={{ position: "relative", padding: "0 16px 14px" }}>
      {/* Autocomplete popup */}
      {matches.length > 0 && (
        <div style={{
          position: "absolute", bottom: "100%", left: 16, right: 16,
          marginBottom: 6,
          background: "var(--cb-bg2)", border: "1px solid var(--cb-border-bright)",
          borderRadius: "var(--cb-radius-md)", boxShadow: "var(--cb-shadow-overlay)",
          overflow: "hidden", zIndex: 10,
        }}>
          {matches.map((c, i) => (
            <div key={c.name}
                 onMouseDown={(e) => { e.preventDefault(); complete(c.name); }}
                 onMouseEnter={() => setSel(i)}
                 style={{
                   display: "flex", gap: 10, alignItems: "baseline",
                   padding: "6px 12px", cursor: "pointer", fontSize: 12,
                   background: i === sel ? "var(--cb-bg3)" : "transparent",
                 }}>
              <span className="mono" style={{ color: "var(--cb-cyan)" }}>/{c.name}</span>
              <span className="faint" style={{ flex: 1, fontSize: 11,
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap" }}>
                {c.description}
              </span>
            </div>
          ))}
        </div>
      )}

      <div style={{
        display: "flex", gap: 8, alignItems: "flex-end",
        border: "1px solid var(--cb-border-bright)",
        borderRadius: "var(--cb-radius-lg)",
        background: "var(--cb-bg1)", padding: "8px 8px 8px 14px",
      }}>
        <textarea
          ref={ref}
          rows={1}
          value={text}
          disabled={disabled}
          placeholder="Ask CERBERUS, or type / for commands…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (matches.length > 0) {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setSel((s) => Math.min(s + 1, matches.length - 1));
                return;
              }
              if (e.key === "ArrowUp") {
                e.preventDefault();
                setSel((s) => Math.max(s - 1, 0));
                return;
              }
              if (e.key === "Tab" || (e.key === "Enter" && text.endsWith(" "))) {
                e.preventDefault();
                complete(matches[sel].name);
                return;
              }
            }
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          style={{
            flex: 1, resize: "none", border: "none", background: "transparent",
            padding: 0, fontSize: 13, maxHeight: 140, outline: "none",
            fontFamily: "var(--cb-font-ui)",
          }}
        />
        <button onClick={send} disabled={disabled || !text.trim()}
                title="Send (Enter)"
                style={{
                  padding: "6px 14px", borderRadius: "var(--cb-radius-md)",
                  background: "linear-gradient(135deg, var(--cb-cyan), var(--cb-blue))",
                  color: "#04121a", fontWeight: 700, fontSize: 12.5,
                }}>
          Send
        </button>
      </div>
      <div className="faint" style={{ fontSize: 10, marginTop: 5, padding: "0 2px" }}>
        Enter to send · Shift+Enter for newline · / for commands · Ctrl+K palette
      </div>
    </div>
  );
}
