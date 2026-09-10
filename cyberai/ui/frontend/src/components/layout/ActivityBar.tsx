/**
 * Activity bar (icon rail) + sidebar panel. The sidebar hosts the
 * chat list / session history / explorer depending on the active view.
 */

import { useApp } from "@/stores/app";
import type { ViewId } from "@/stores/app";

const NAV: Array<{ id: ViewId; icon: string; label: string }> = [
  { id: "chat", icon: "💬", label: "Chat" },
  { id: "dashboard", icon: "◉", label: "Dashboard" },
  { id: "missions", icon: "▶", label: "Missions" },
  { id: "findings", icon: "⚑", label: "Findings" },
  { id: "targets", icon: "◎", label: "Targets" },
  { id: "agents", icon: "⬡", label: "Agents" },
  { id: "tools", icon: "⚒", label: "Tools" },
  { id: "models", icon: "⬢", label: "Models" },
  { id: "security", icon: "⛨", label: "Security" },
  { id: "memory", icon: "◈", label: "Memory" },
  { id: "evidence", icon: "▤", label: "Evidence" },
  { id: "sessions", icon: "☰", label: "Sessions" },
  { id: "workspace", icon: "▦", label: "Workspace" },
  { id: "events", icon: "≋", label: "Events" },
];

export function ActivityBar() {
  const { state, dispatch } = useApp();
  return (
    <nav style={{
      width: 44, flexShrink: 0, display: "flex", flexDirection: "column",
      background: "var(--cb-bg1)", borderRight: "1px solid var(--cb-border)",
      padding: "6px 0", gap: 2, overflowY: "auto",
    }}>
      {NAV.map((item) => {
        const active = state.view === item.id;
        return (
          <button key={item.id}
                  title={item.label}
                  onClick={() => dispatch({ type: "SET_VIEW", view: item.id })}
                  style={{
                    position: "relative", height: 40,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: active ? "var(--cb-cyan)" : "var(--cb-text-faint)",
                    fontSize: 16,
                  }}>
            {item.icon}
            {active && <span style={{
              position: "absolute", left: 0, top: 8, bottom: 8, width: 2,
              background: "var(--cb-cyan)",
            }} />}
          </button>
        );
      })}
    </nav>
  );
}
