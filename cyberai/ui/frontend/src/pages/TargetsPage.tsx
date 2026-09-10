/**
 * Targets — authorization-gated target cards.
 */

import { targetsApi } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill, stateTone } from "@/components/common/Pill";

export function TargetsPage() {
  const toast = useToast();
  const { data, loading, error, refresh } = useFetch(() => targetsApi.list(), []);

  const toggle = async (id: string, authorize: boolean) => {
    try {
      await (authorize ? targetsApi.authorize(id) : targetsApi.revoke(id));
      toast("success", authorize ? "target authorized" : "authorization revoked");
      await refresh();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "update failed");
    }
  };

  const targets = data?.targets ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Targets" subtitle={`${data?.total ?? 0} known · authorization required for active testing`} />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>
        {error && <ErrorBox error={error} />}
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
            <Spinner size={22} />
          </div>
        )}
        {!loading && targets.length === 0 && (
          <EmptyState icon="◎" title="No targets"
                       hint="Targets are discovered by missions or added via the CLI. Authorization is required before active testing." />
        )}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
                      gap: 12 }}>
          {targets.map((t) => (
            <div key={t.id} style={{
              background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
              borderRadius: "var(--cb-radius-md)", padding: 14,
              display: "flex", flexDirection: "column", gap: 8,
            }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Pill tone={stateTone(t.state)}>{t.state}</Pill>
                <span className="mono" style={{ fontSize: 12.5, fontWeight: 600,
                                                 overflow: "hidden",
                                                 textOverflow: "ellipsis",
                                                 whiteSpace: "nowrap" }}>
                  {t.id}
                </span>
              </div>
              <span className="mono faint" style={{ fontSize: 11 }}>
                {t.host}:{t.port}{t.protocol ? ` · ${t.protocol}` : ""}
              </span>
              {t.description && <span className="dim" style={{ fontSize: 11.5 }}>{t.description}</span>}
              <div style={{ flex: 1 }} />
              <div>
                {t.state === "UNAUTHORIZED" ? (
                  <button onClick={() => void toggle(t.id, true)}
                          style={{ fontSize: 11, padding: "4px 12px", width: "100%",
                                   color: "var(--cb-green)",
                                   border: "1px solid var(--cb-green)44", borderRadius: 4,
                                   background: "transparent" }}>
                    AUTHORIZE
                  </button>
                ) : (
                  <button onClick={() => void toggle(t.id, false)}
                          style={{ fontSize: 11, padding: "4px 12px", width: "100%",
                                   color: "var(--cb-red)",
                                   border: "1px solid var(--cb-red)44", borderRadius: 4,
                                   background: "transparent" }}>
                    REVOKE
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
