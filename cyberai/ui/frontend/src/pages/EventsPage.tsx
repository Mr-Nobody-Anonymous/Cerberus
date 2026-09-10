/**
 * Events — full live event feed (from the SSE ring buffer).
 */

import { useApp } from "@/stores/app";
import { PageHeader, EmptyState } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

const typeColor: Record<string, string> = {
  "policy.blocked": "var(--cb-red)",
  "approval.required": "var(--cb-yellow)",
  "approval.granted": "var(--cb-green)",
  "approval.denied": "var(--cb-red)",
  "audit": "var(--cb-text-faint)",
  "task_result": "var(--cb-green)",
  "task_error": "var(--cb-red)",
};

export function EventsPage() {
  const { state } = useApp();
  const events = [...state.events].reverse(); // newest first

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Events" subtitle={`${state.events.length} buffered · ${state.sseUp ? "streaming" : "stream down"}`}
                  actions={
                    <Pill tone={state.sseUp ? "ok" : "error"}>
                      {state.sseUp ? "SSE CONNECTED" : "SSE DOWN"}
                    </Pill>
                  } />
      <div style={{ flex: 1, overflowY: "auto", padding: "14px 18px" }}>
        {events.length === 0 && (
          <EmptyState icon="≋" title="No events yet"
                       hint="Events stream in live from missions, policy decisions, and audits." />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {events.map((ev, i) => {
            const color = typeColor[ev.type] ?? "var(--cb-cyan)";
            return (
              <div key={i} style={{
                display: "flex", gap: 10, alignItems: "baseline",
                background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
                borderRadius: "var(--cb-radius-sm)", padding: "6px 12px",
                fontFamily: "var(--cb-font-mono)", fontSize: 11,
              }}>
                <span style={{ color, flexShrink: 0, width: 8 }}>●</span>
                <span style={{ color: "var(--cb-text-dim)", flexShrink: 0,
                               minWidth: 110 }}>
                  {ev.type}
                </span>
                <span className="faint" style={{
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  flex: 1,
                }}>
                  {JSON.stringify(ev.data ?? {}).slice(0, 160)}
                </span>
                <span className="faint" style={{ flexShrink: 0 }}>
                  {ev.timestamp
                    ? new Date(ev.timestamp).toLocaleTimeString()
                    : typeof ev.ts === "number"
                      ? new Date(ev.ts * 1000).toLocaleTimeString()
                      : ""}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
