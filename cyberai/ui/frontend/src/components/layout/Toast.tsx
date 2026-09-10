/**
 * Toast notifications — bottom-right, auto-dismiss.
 */

import { useApp } from "@/stores/app";

export function Toast() {
  const { state } = useApp();
  if (!state.toast) return null;
  const tone = state.toast.kind === "error" ? "var(--cb-red)"
    : state.toast.kind === "success" ? "var(--cb-green)" : "var(--cb-cyan)";
  return (
    <div style={{
      position: "fixed", bottom: 18, right: 18, zIndex: 200,
      background: "var(--cb-bg2)", border: `1px solid ${tone}66`,
      borderRadius: "var(--cb-radius-md)", boxShadow: "var(--cb-shadow-overlay)",
      padding: "10px 16px", fontSize: 12.5,
      color: "var(--cb-text)", maxWidth: 380,
      display: "flex", gap: 8, alignItems: "center",
    }}>
      <span style={{ color: tone, fontWeight: 700 }}>
        {state.toast.kind === "error" ? "✕" : state.toast.kind === "success" ? "✓" : "ℹ"}
      </span>
      {state.toast.text}
    </div>
  );
}
