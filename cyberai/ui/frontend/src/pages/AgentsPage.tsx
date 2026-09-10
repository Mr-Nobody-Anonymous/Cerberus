/**
 * Agents — the 7 base agents with performance stats.
 */

import { agentsApi } from "@/lib/api";
import { useFetch } from "@/hooks";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

const AGENT_META: Record<string, { icon: string; desc: string }> = {
  planner: { icon: "⬡", desc: "Decomposes objectives into task graphs" },
  researcher: { icon: "◈", desc: "Gathers intelligence and prior knowledge" },
  recon: { icon: "◎", desc: "Maps target surface (ports, services, versions)" },
  analyst: { icon: "⬢", desc: "Correlates evidence into findings" },
  coder: { icon: "⚒", desc: "Writes tooling and exploit scaffolds" },
  verifier: { icon: "⛨", desc: "Validates findings before promotion" },
  reporter: { icon: "▤", desc: "Assembles mission reports" },
};

export function AgentsPage() {
  const { data, loading, error } = useFetch(() => agentsApi.list(), []);

  if (error) return <ErrorBox error={error} />;
  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const agents = data?.agents ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Agents" subtitle="specialist workers" />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>
        {agents.length === 0 && (
          <EmptyState icon="⬡" title="No agents loaded" />
        )}
        <div style={{ display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                      gap: 12 }}>
          {agents.map((a) => {
            const meta = AGENT_META[a.name] ?? { icon: "⬡", desc: "" };
            return (
              <div key={a.name} style={{
                background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
                borderRadius: "var(--cb-radius-md)", padding: 14,
                display: "flex", flexDirection: "column", gap: 8,
              }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <div style={{
                    width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    background: "var(--cb-bg3)", color: "var(--cb-cyan)",
                    border: "1px solid var(--cb-cyan)44", fontSize: 15,
                  }}>
                    {meta.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{a.name}</div>
                    <div className="faint" style={{ fontSize: 10.5 }}>{meta.desc}</div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <Pill tone="neutral">{a.calls} calls</Pill>
                  {a.success_rate !== null && a.success_rate !== undefined && (
                    <Pill tone={a.success_rate >= 0.8 ? "ok"
                          : a.success_rate >= 0.5 ? "warn" : "error"}>
                      {Math.round(a.success_rate * 100)}% success
                    </Pill>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
