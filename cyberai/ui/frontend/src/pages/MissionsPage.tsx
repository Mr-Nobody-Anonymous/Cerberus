/**
 * Missions — launch pad (safest mode default) + mission list + detail.
 */

import { useState } from "react";
import { missionsApi } from "@/lib/api";
import type { SessionRow } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { useApp } from "@/stores/app";
import { PageHeader, EmptyState } from "@/components/common/Basics";
import { Pill, stateTone } from "@/components/common/Pill";

const MODES = [
  { id: "SIMULATE", desc: "Safest — full pipeline, no real actions", tone: "warn" as const },
  { id: "PLAN", desc: "Dry-run — plan only, no execution", tone: "violet" as const },
  { id: "LAB", desc: "Active testing on authorized lab targets", tone: "info" as const },
  { id: "AUTHORIZED", desc: "Active testing — requires authorization", tone: "error" as const },
];

export function MissionsPage() {
  const toast = useToast();
  const { dispatch } = useApp();
  const [objective, setObjective] = useState("");
  const [mode, setMode] = useState("SIMULATE");
  const [launching, setLaunching] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const { data, refresh } = useFetch(() => missionsApi.list(), []);

  const launch = async () => {
    const obj = objective.trim();
    if (!obj) { toast("error", "objective is required"); return; }
    setLaunching(true);
    try {
      const res = await missionsApi.launch(obj, mode);
      toast("success", `mission launched (${res.mode})`);
      setObjective("");
      await refresh();
      setSelected(res.session_id);
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "launch failed");
    } finally {
      setLaunching(false);
    }
  };

  const stop = async (id: string) => {
    try {
      await missionsApi.stop(id);
      toast("info", "stop requested");
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "stop failed");
    }
  };

  const missions = data?.missions ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Missions" subtitle="launch and monitor" />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>

        {/* Mission composer */}
        <div style={{
          background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
          borderRadius: "var(--cb-radius-lg)", padding: 16, marginBottom: 18,
        }}>
          <div style={{ fontSize: 12, color: "var(--cb-text-dim)", marginBottom: 10,
                        textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Mission Composer
          </div>
          <textarea
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="Objective, e.g. 'Assess the lab web target for exposed services and misconfigurations'"
            rows={2}
            style={{ width: "100%", resize: "vertical", marginBottom: 12, fontSize: 13 }}
          />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            {MODES.map((m) => (
              <button key={m.id}
                      onClick={() => setMode(m.id)}
                      title={m.desc}
                      style={{
                        padding: "5px 12px", borderRadius: 999,
                        border: `1px solid ${mode === m.id ? "var(--cb-cyan)" : "var(--cb-border)"}`,
                        color: mode === m.id ? "var(--cb-cyan)" : "var(--cb-text-dim)",
                        fontSize: 11.5, fontWeight: 600, letterSpacing: "0.04em",
                        background: mode === m.id ? "var(--cb-cyan)12" : "transparent",
                      }}>
                {m.id}
              </button>
            ))}
          </div>
          <div className="faint" style={{ fontSize: 11, marginBottom: 12 }}>
            {MODES.find((m) => m.id === mode)?.desc}
          </div>
          <button onClick={() => void launch()} disabled={launching || !objective.trim()}
                  style={{
                    padding: "8px 22px", borderRadius: "var(--cb-radius-md)",
                    background: "linear-gradient(135deg, var(--cb-cyan), var(--cb-blue))",
                    color: "#04121a", fontWeight: 700, fontSize: 13,
                  }}>
            {launching ? "Launching…" : "Launch Mission"}
          </button>
        </div>

        {/* Mission list */}
        {missions.length === 0 ? (
          <EmptyState icon="▶" title="No missions yet"
                       hint="Use the composer above to launch your first mission. SIMULATE mode is the safest starting point." />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {missions.map((m: SessionRow) => (
              <div key={m.id}
                   onClick={() => { setSelected(m.id); dispatch({ type: "SET_ACTIVE_SESSION", id: m.id }); }}
                   style={{
                     display: "flex", gap: 10, alignItems: "center",
                     background: selected === m.id ? "var(--cb-bg3)" : "var(--cb-bg2)",
                     border: `1px solid ${selected === m.id ? "var(--cb-border-bright)" : "var(--cb-border)"}`,
                     borderRadius: "var(--cb-radius-sm)", padding: "9px 12px",
                     cursor: "pointer",
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
                <button onClick={(e) => { e.stopPropagation(); void stop(m.id); }}
                        title="Stop mission"
                        style={{ color: "var(--cb-red)", fontSize: 11,
                                 padding: "2px 8px", border: "1px solid var(--cb-red)44",
                                 borderRadius: 4 }}>
                  STOP
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
