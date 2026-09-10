/**
 * Dashboard — system overview: status cards, quick stats, recent activity.
 */

import { useFetch } from "@/hooks";
import { findingsApi, missionsApi, targetsApi, agentsApi, modelsApi } from "@/lib/api";
import { PageHeader, Spinner, ErrorBox } from "@/components/common/Basics";
import { Pill, stateTone } from "@/components/common/Pill";
import { useApp } from "@/stores/app";

function StatCard({ label, value, tone, hint }: {
  label: string; value: string | number; tone?: string; hint?: string;
}) {
  return (
    <div style={{
      background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
      borderRadius: "var(--cb-radius-md)", padding: "14px 16px",
      display: "flex", flexDirection: "column", gap: 4, minWidth: 140,
    }}>
      <span className="faint" style={{ fontSize: 10.5, textTransform: "uppercase",
                                       letterSpacing: "0.08em" }}>{label}</span>
      <span style={{ fontSize: 24, fontWeight: 700, color: tone ?? "var(--cb-text)" }}>
        {value}
      </span>
      {hint && <span className="faint" style={{ fontSize: 10.5 }}>{hint}</span>}
    </div>
  );
}

export function DashboardPage() {
  const { state } = useApp();
  const findings = useFetch(() => findingsApi.list({ limit: 1000 }), []);
  const missions = useFetch(() => missionsApi.list(), []);
  const targets = useFetch(() => targetsApi.list(), []);
  const agents = useFetch(() => agentsApi.list(), []);
  const models = useFetch(() => modelsApi.list(), []);

  if (findings.error) return <ErrorBox error={findings.error} />;
  if (findings.loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const byStatus = (findings.data?.findings ?? []).reduce<Record<string, number>>((acc, f) => {
    const s = (f.status as string) || "UNVERIFIED";
    acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {});

  const activeTargets = (targets.data?.targets ?? []).filter((t) => t.state === "ACTIVE").length;
  const unauthTargets = (targets.data?.targets ?? []).filter((t) => t.state === "UNAUTHORIZED").length;

  return (
    <div style={{ overflowY: "auto", height: "100%" }}>
      <PageHeader title="Dashboard" subtitle="system overview" />
      <div style={{ padding: "18px 18px 30px", display: "flex", flexDirection: "column",
                    gap: 20 }}>

        {/* Stat cards */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <StatCard label="Findings" value={findings.data?.total ?? 0}
                    hint={`${byStatus.VERIFIED ?? 0} verified · ${byStatus.LIKELY ?? 0} likely`} />
          <StatCard label="Missions" value={missions.data?.total ?? 0} tone="var(--cb-violet)" />
          <StatCard label="Targets" value={targets.data?.total ?? 0}
                    tone="var(--cb-cyan)"
                    hint={`${activeTargets} active · ${unauthTargets} unauthorized`} />
          <StatCard label="Agents" value={agents.data?.agents.length ?? 0} />
          <StatCard label="Models" value={models.data?.models.length ?? 0} />
          <StatCard label="Events" value={state.events.length}
                    tone={state.sseUp ? "var(--cb-green)" : "var(--cb-red)"}
                    hint={state.sseUp ? "streaming live" : "stream down"} />
        </div>

        {/* Findings breakdown */}
        <div>
          <h2 style={{ fontSize: 13, marginBottom: 10, color: "var(--cb-text-dim)" }}>
            Findings by verification status
          </h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {Object.entries(byStatus).map(([s, n]) => (
              <Pill key={s} tone={stateTone(s)}>{s} · {n}</Pill>
            ))}
          </div>
        </div>

        {/* Recent missions */}
        <div>
          <h2 style={{ fontSize: 13, marginBottom: 10, color: "var(--cb-text-dim)" }}>
            Recent missions
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(missions.data?.missions ?? []).slice(0, 5).map((m) => (
              <div key={m.id} style={{
                display: "flex", gap: 10, alignItems: "center",
                background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
                borderRadius: "var(--cb-radius-sm)", padding: "8px 12px",
              }}>
                <Pill tone={stateTone(m.status)}>{m.status || "RUNNING"}</Pill>
                <Pill tone="violet">{m.mode}</Pill>
                <span style={{ fontSize: 12, flex: 1, overflow: "hidden",
                               textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {m.objective}
                </span>
                <span className="faint mono" style={{ fontSize: 10.5 }}>
                  {m.started_at ? new Date(m.started_at).toLocaleString() : ""}
                </span>
              </div>
            ))}
            {(missions.data?.missions ?? []).length === 0 && (
              <span className="faint" style={{ fontSize: 12 }}>No missions yet.</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
