/**
 * Right panel — live event stream (activity feed) + quick security summary.
 * Collapsible via Ctrl+J.
 */

import { useApp } from "@/stores/app";
import { useFetch } from "@/hooks";
import { securityApi } from "@/lib/api";
import { Collapsible } from "./Collapsible";
import { Pill } from "@/components/common/Pill";

const eventColor: Record<string, string> = {
  "policy.blocked": "var(--cb-red)",
  "approval.required": "var(--cb-yellow)",
  "approval.granted": "var(--cb-green)",
  "approval.denied": "var(--cb-red)",
  "audit": "var(--cb-text-faint)",
  "task_result": "var(--cb-green)",
  "task_error": "var(--cb-red)",
};

export function RightPanel() {
  const { state } = useApp();
  const { data: sec } = useFetch(() => securityApi.center(), [state.events.length]);

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      background: "var(--cb-bg1)", overflowY: "auto",
    }}>
      <Collapsible title="Live Activity" defaultOpen>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {state.events.length === 0 && (
            <div className="faint" style={{ fontSize: 11.5, padding: "4px 0" }}>
              Waiting for events…
            </div>
          )}
          {state.events.slice(0, 40).map((ev, i) => {
            const color = eventColor[ev.type] ?? "var(--cb-cyan)";
            const data = ev.data ?? {};
            const text = typeof data.action === "string" ? data.action
              : typeof data.error === "string" ? data.error
              : JSON.stringify(data).slice(0, 90);
            return (
              <div key={i} style={{
                display: "flex", gap: 7, alignItems: "baseline",
                fontSize: 11, fontFamily: "var(--cb-font-mono)",
                padding: "2px 0",
              }}>
                <span style={{ color, flexShrink: 0, width: 8 }}>●</span>
                <span style={{ color: "var(--cb-text-dim)", flexShrink: 0 }}>
                  {ev.type}
                </span>
                <span className="faint" style={{
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {text}
                </span>
              </div>
            );
          })}
        </div>
      </Collapsible>

      <Collapsible title="Security" defaultOpen>
        {sec && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <Pill tone="violet">{sec.policy.mode}</Pill>
              <Pill tone="ok">{sec.policy.targets_authorized} authorized</Pill>
              <Pill tone={sec.approvals_pending > 0 ? "warn" : "neutral"}>
                {sec.approvals_pending} pending
              </Pill>
            </div>
            {sec.blocked_actions.length > 0 && (
              <div className="faint" style={{ fontSize: 11 }}>
                {sec.blocked_actions.length} blocked action(s) — see Security view
              </div>
            )}
          </div>
        )}
      </Collapsible>
    </div>
  );
}
