/**
 * Security Center — policy state, blocked actions, approval queue.
 * This is the authorization surface: nothing here can bypass PolicyEngine.
 */

import { securityApi } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { useApp } from "@/stores/app";
import { PageHeader, Spinner, ErrorBox } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

export function SecurityPage() {
  const toast = useToast();
  const { state } = useApp();
  const { data, loading, error, refresh } = useFetch(() => securityApi.center(), [state.events.length]);
  const approvals = useFetch(() => securityApi.approvals(), [state.events.length]);

  const decide = async (id: string, approve: boolean) => {
    try {
      await (approve ? securityApi.approve(id) : securityApi.deny(id));
      toast("success", approve ? "approved" : "denied");
      await Promise.all([refresh(), approvals.refresh()]);
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "decision failed");
    }
  };

  if (error) return <ErrorBox error={error} />;
  if (loading || !data) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Security Center" subtitle="policy · approvals · audit" />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>

        {/* Policy state */}
        <div style={{
          background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
          borderRadius: "var(--cb-radius-lg)", padding: 14, marginBottom: 18,
          display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center",
        }}>
          <Pill tone="violet">{data.policy.mode}</Pill>
          <Pill tone="ok">{data.policy.targets_authorized} targets authorized</Pill>
          <Pill tone={data.approvals_pending > 0 ? "warn" : "neutral"}>
            {data.approvals_pending} pending approvals
          </Pill>
          <Pill tone={data.blocked_actions.length > 0 ? "error" : "neutral"}>
            {data.blocked_actions.length} blocked actions
          </Pill>
        </div>

        {/* Approvals */}
        <h2 style={{ fontSize: 13, color: "var(--cb-text-dim)", marginBottom: 10 }}>
          Pending Approvals
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 22 }}>
          {(approvals.data?.pending ?? []).length === 0 && (
            <span className="faint" style={{ fontSize: 12 }}>No pending approvals.</span>
          )}
          {(approvals.data?.pending ?? []).map((a) => (
            <div key={a.id} style={{
              background: "var(--cb-bg2)", border: "1px solid var(--cb-yellow)44",
              borderRadius: "var(--cb-radius-sm)", padding: "10px 14px",
              display: "flex", gap: 10, alignItems: "center",
            }}>
              <Pill tone="warn">PENDING</Pill>
              <span style={{ fontSize: 12, flex: 1, overflow: "hidden",
                             textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {a.action}
              </span>
              <button onClick={() => void decide(a.id, true)}
                      style={{ fontSize: 10.5, padding: "3px 10px",
                               color: "var(--cb-green)",
                               border: "1px solid var(--cb-green)44", borderRadius: 4 }}>
                APPROVE
              </button>
              <button onClick={() => void decide(a.id, false)}
                      style={{ fontSize: 10.5, padding: "3px 10px",
                               color: "var(--cb-red)",
                               border: "1px solid var(--cb-red)44", borderRadius: 4 }}>
                DENY
              </button>
            </div>
          ))}
        </div>

        {/* Blocked actions */}
        <h2 style={{ fontSize: 13, color: "var(--cb-text-dim)", marginBottom: 10 }}>
          Blocked Actions (recent)
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {data.blocked_actions.length === 0 && (
            <span className="faint" style={{ fontSize: 12 }}>Nothing blocked recently.</span>
          )}
          {data.blocked_actions.slice(0, 30).map((b, i) => {
            const entry = b as { action?: string; reason?: string; timestamp?: string };
            return (
            <div key={i} style={{
              display: "flex", gap: 10, alignItems: "baseline",
              background: "var(--cb-bg2)", border: "1px solid var(--cb-red)33",
              borderRadius: "var(--cb-radius-sm)", padding: "7px 12px",
              fontFamily: "var(--cb-font-mono)", fontSize: 11,
            }}>
              <span style={{ color: "var(--cb-red)" }}>✕</span>
              <span style={{ color: "var(--cb-text-dim)" }}>
                {entry.action || entry.reason || JSON.stringify(b).slice(0, 120)}
              </span>
              <span className="faint" style={{ marginLeft: "auto", flexShrink: 0 }}>
                {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ""}
              </span>
            </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
