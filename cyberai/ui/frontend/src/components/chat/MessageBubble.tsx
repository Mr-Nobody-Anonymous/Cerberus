/**
 * Message bubble — user / assistant / system / event roles.
 * Assistant content may be JSON (command output) → pretty-printed.
 */

import { useMemo } from "react";
import type { ChatMessage } from "@/lib/api";

function prettyContent(content: string): { text: string; isJson: boolean } {
  const trimmed = content.trim();
  if ((trimmed.startsWith("{") && trimmed.endsWith("}")) ||
      (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
    try {
      return { text: JSON.stringify(JSON.parse(trimmed), null, 2), isJson: true };
    } catch { /* not JSON */ }
  }
  return { text: content, isJson: false };
}

const roleStyle: Record<string, { label: string; color: string; bg: string }> = {
  user: { label: "YOU", color: "var(--cb-blue)", bg: "var(--cb-bg2)" },
  assistant: { label: "CERBERUS", color: "var(--cb-cyan)", bg: "var(--cb-bg1)" },
  system: { label: "SYSTEM", color: "var(--cb-yellow)", bg: "var(--cb-bg1)" },
  event: { label: "EVENT", color: "var(--cb-violet)", bg: "var(--cb-bg1)" },
};

export function MessageBubble({ msg }: { msg: ChatMessage }) {
  const style = roleStyle[msg.role] ?? roleStyle.system;
  const pretty = useMemo(() => prettyContent(msg.content), [msg.content]);
  const isUser = msg.role === "user";

  return (
    <div style={{
      display: "flex", gap: 10,
      justifyContent: isUser ? "flex-end" : "flex-start",
      padding: "3px 16px",
    }}>
      {!isUser && (
        <div style={{
          flexShrink: 0, width: 30, height: 30, borderRadius: "50%",
          display: "flex", alignItems: "center", justifyContent: "center",
          background: `var(--cb-bg3)`, color: style.color,
          fontSize: 11, fontWeight: 700, fontFamily: "var(--cb-font-mono)",
          border: `1px solid ${style.color}44`,
        }}>
          {msg.role === "assistant" ? "Ω" : msg.role === "event" ? "≋" : "!"}
        </div>
      )}
      <div style={{
        maxWidth: "78%", minWidth: 0,
        background: isUser ? "linear-gradient(135deg, var(--cb-bg3), var(--cb-bg2))" : style.bg,
        border: `1px solid ${isUser ? "var(--cb-border-bright)" : "var(--cb-border)"}`,
        borderRadius: isUser ? "12px 12px 4px 12px" : "12px 12px 12px 4px",
        padding: "8px 12px",
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8, marginBottom: 4,
          fontSize: 10, letterSpacing: "0.08em",
        }}>
          <span style={{ color: style.color, fontWeight: 700 }}>{style.label}</span>
          {msg.model && <span className="faint">{msg.model}</span>}
          <span className="faint">
            {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ""}
          </span>
        </div>
        <pre style={{
          margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere",
          fontFamily: pretty.isJson ? "var(--cb-font-mono)" : "var(--cb-font-ui)",
          fontSize: pretty.isJson ? 11.5 : 13,
          lineHeight: 1.55,
          color: "var(--cb-text)",
        }}>
          {pretty.text}
        </pre>
      </div>
    </div>
  );
}
