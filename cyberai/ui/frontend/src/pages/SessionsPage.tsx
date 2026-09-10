/**
 * Sessions — mission/session timeline.
 */

import { sessionsApi } from "@/lib/api";
import { useFetch } from "@/hooks";
import { useApp } from "@/stores/app";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill, stateTone } from "@/components/common/Pill";

export function SessionsPage() {
  const { dispatch } = useApp();
  const { data, loading, error } = useFetch(() => sessionsApi.list(), []);

  if (error) return <ErrorBox error={error} />;
  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const sessions = data?.sessions ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Sessions" subtitle={`${data?.total ?? sessions.length} recorded`} />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>
        {sessions.length === 0 && (
          <EmptyState icon="▦" title="No sessions"
                       hint="Sessions are created by missions and chat conversations." />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {sessions.map((s) => (
            <div key={s.id}
                 onClick={() => dispatch({ type: "SET_ACTIVE_SESSION", id: s.id })}
                 style={{
                   display: "flex", gap: 10, alignItems: "center",
                   background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
                   borderRadius: "var(--cb-radius-sm)", padding: "9px 14px",
                   cursor: "pointer",
                 }}>
              <Pill tone={stateTone(s.status)}>{s.status || "—"}</Pill>
              {s.kind && <Pill tone="violet">{s.kind}</Pill>}
              <span style={{ fontSize: 12, flex: 1, overflow: "hidden",
                             textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {s.objective || s.title || s.id}
              </span>
              <span className="faint mono" style={{ fontSize: 10.5 }}>
                {s.started_at ? new Date(s.started_at).toLocaleString() : ""}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
