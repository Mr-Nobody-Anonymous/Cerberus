/**
 * Evidence — collected artifacts across all sessions.
 */

import { evidenceApi } from "@/lib/api";
import { useFetch } from "@/hooks";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

export function EvidencePage() {
  const { data, loading, error } = useFetch(() => evidenceApi.list(), []);

  if (error) return <ErrorBox error={error} />;
  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const items = data?.evidence ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Evidence" subtitle={`${data?.total ?? items.length} artifacts`} />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>
        {items.length === 0 && (
          <EmptyState icon="▤" title="No evidence collected"
                       hint="Evidence is captured during missions and stored per session." />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {items.map((e) => (
            <div key={e.id} style={{
              background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
              borderRadius: "var(--cb-radius-sm)", padding: "10px 14px",
            }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                {e.type && <Pill tone="violet">{e.type}</Pill>}
                <span className="mono" style={{ fontSize: 12, flex: 1,
                               overflow: "hidden", textOverflow: "ellipsis",
                               whiteSpace: "nowrap" }}>
                  {e.source}
                </span>
                <Pill tone={e.verification_status === "VERIFIED" ? "ok"
                       : e.verification_status === "REJECTED" ? "error" : "warn"}>
                  {e.verification_status}
                </Pill>
                <span className="faint mono" style={{ fontSize: 10 }}>
                  {e.session_id ? String(e.session_id).slice(0, 8) : ""}
                </span>
              </div>
              {typeof e.content === "string" && (
                <div className="dim" style={{ fontSize: 11.5, lineHeight: 1.5 }}>
                  {e.content.length > 300 ? `${e.content.slice(0, 300)}…` : e.content}
                </div>
              )}
              <div className="faint mono" style={{ fontSize: 10, marginTop: 4 }}>
                {e.timestamp} · confidence {e.confidence}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
