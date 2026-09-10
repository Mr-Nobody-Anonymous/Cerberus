/**
 * Top bar — brand, system status pills, SSE indicator, palette trigger.
 */

import { useApp } from "@/stores/app";
import { Pill } from "@/components/common/Pill";

export function TopBar() {
  const { state, dispatch } = useApp();
  const sse = state.sseUp === null ? "CONNECTING" : state.sseUp ? "LIVE" : "DOWN";
  const sseTone = state.sseUp === null ? "warn" : state.sseUp ? "ok" : "error";

  return (
    <header style={{
      display: "flex", alignItems: "center", gap: 14,
      height: 42, padding: "0 14px",
      borderBottom: "1px solid var(--cb-border)",
      background: "var(--cb-bg1)", flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{
          fontSize: 15, fontWeight: 800, letterSpacing: "0.14em",
          background: "linear-gradient(90deg, var(--cb-cyan), var(--cb-violet))",
          WebkitBackgroundClip: "text", backgroundClip: "text",
          color: "transparent",
        }}>CERBERUS</span>
        <span className="faint" style={{ fontSize: 10 }}>v2.0</span>
      </div>

      {/* Palette trigger */}
      <button
        onClick={() => dispatch({ type: "PALETTE_OPEN", open: true })}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          width: 300, padding: "4px 10px",
          background: "var(--cb-bg0)", border: "1px solid var(--cb-border)",
          borderRadius: "var(--cb-radius-sm)",
          color: "var(--cb-text-faint)", fontSize: 12,
        }}>
        <span style={{ fontSize: 11 }}>⌕</span>
        <span style={{ flex: 1, textAlign: "left" }}>Search or run a command…</span>
        <kbd style={{
          padding: "0 5px", border: "1px solid var(--cb-border-bright)",
          borderRadius: 4, fontSize: 10, fontFamily: "var(--cb-font-mono)",
        }}>Ctrl K</kbd>
      </button>

      <div style={{ flex: 1 }} />

      {/* Status pills */}
      <Pill tone="ok" title="Local-only mode: all operations stay on this machine">
        LOCAL-ONLY
      </Pill>
      <Pill tone="violet" title="Active testing restricted to authorized lab targets">
        LAB-ONLY
      </Pill>
      <Pill tone={sseTone as "ok" | "warn" | "error"} title="Live event stream (SSE)">
        SSE {sse}
      </Pill>
    </header>
  );
}
