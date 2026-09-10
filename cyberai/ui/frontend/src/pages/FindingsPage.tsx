/**
 * Findings — triage table with verify/reject actions.
 */

import { useState } from "react";
import { findingsApi } from "@/lib/api";
import type { Finding } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill, stateTone } from "@/components/common/Pill";

const FILTERS = ["ALL", "UNVERIFIED", "LIKELY", "VERIFIED", "REJECTED"];

export function FindingsPage() {
  const toast = useToast();
  const [filter, setFilter] = useState("ALL");
  const [q, setQ] = useState("");
  const { data, loading, error, refresh } = useFetch(
    () => findingsApi.list({ status: filter === "ALL" ? undefined : filter, q: q || undefined, limit: 200 }),
    [filter, q],
  );

  const setStatus = async (f: Finding, status: string) => {
    try {
      await findingsApi.setStatus(f.id, status);
      toast("success", `finding marked ${status}`);
      await refresh();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "update failed");
    }
  };

  const findings = data?.findings ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Findings" subtitle={`${data?.total ?? 0} total`} />
      <div style={{ padding: "0 18px 10px", display: "flex", gap: 8, flexWrap: "wrap",
                    alignItems: "center" }}>
        {FILTERS.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
                  style={{
                    padding: "4px 12px", borderRadius: 999, fontSize: 11,
                    fontWeight: 600, letterSpacing: "0.04em",
                    border: `1px solid ${filter === s ? "var(--cb-cyan)" : "var(--cb-border)"}`,
                    color: filter === s ? "var(--cb-cyan)" : "var(--cb-text-dim)",
                    background: filter === s ? "var(--cb-cyan)12" : "transparent",
                  }}>
            {s}
          </button>
        ))}
        <input
          value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="search…"
          style={{ marginLeft: "auto", width: 200, fontSize: 12 }}
        />
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "0 18px 18px" }}>
        {error && <ErrorBox error={error} />}
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
            <Spinner size={22} />
          </div>
        )}
        {!loading && findings.length === 0 && (
          <EmptyState icon="⚑" title="No findings"
                       hint="Findings appear here as missions analyze targets. Verify or reject them to build the knowledge base." />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {findings.map((f) => (
            <div key={f.id} style={{
              background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
              borderRadius: "var(--cb-radius-sm)", padding: "10px 14px",
            }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                <Pill tone={stateTone(f.status)}>{f.status}</Pill>
                <span className="faint mono" style={{ fontSize: 10.5 }}>
                  {f.source}
                </span>
                <div style={{ flex: 1 }} />
                {f.status !== "VERIFIED" && (
                  <button onClick={() => void setStatus(f, "VERIFIED")}
                          style={{ fontSize: 10.5, padding: "2px 8px",
                                   color: "var(--cb-green)",
                                   border: "1px solid var(--cb-green)44",
                                   borderRadius: 4 }}>
                    VERIFY
                  </button>
                )}
                {f.status !== "REJECTED" && (
                  <button onClick={() => void setStatus(f, "REJECTED")}
                          style={{ fontSize: 10.5, padding: "2px 8px",
                                   color: "var(--cb-red)",
                                   border: "1px solid var(--cb-red)44",
                                   borderRadius: 4 }}>
                    REJECT
                  </button>
                )}
              </div>
              <div style={{ fontSize: 12.5, lineHeight: 1.5 }}>
                {f.observation}
              </div>
              <div className="faint mono" style={{ fontSize: 10, marginTop: 5 }}>
                {f.session_id ? `session ${f.session_id.slice(0, 8)} · ` : ""}
                {f.created_at ? new Date(f.created_at).toLocaleString() : ""}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
