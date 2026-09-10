/**
 * Models — registry + routing table (view + edit).
 */

import { modelsApi } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { PageHeader, Spinner, ErrorBox } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

export function ModelsPage() {
  const toast = useToast();
  const { data, loading, error, refresh } = useFetch(() => modelsApi.list(), []);
  const routing = useFetch(() => modelsApi.getRouting(), []);

  const setRoute = async (purpose: string, model: string) => {
    try {
      await modelsApi.setRouting(purpose, model);
      toast("success", `route ${purpose} → ${model}`);
      await Promise.all([refresh(), routing.refresh()]);
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "update failed");
    }
  };

  if (error) return <ErrorBox error={error} />;
  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const models = data?.models ?? [];
  const routes = routing.data?.routes ?? {};

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Models" subtitle="local inference registry" />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>

        {/* Routing table */}
        <h2 style={{ fontSize: 13, color: "var(--cb-text-dim)", marginBottom: 10 }}>
          Routing
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 22 }}>
          {Object.entries(routes).map(([purpose, route]) => {
            const model = typeof route === "string"
              ? route
              : (route as { preferred?: string })?.preferred ?? "—";
            return (
            <div key={purpose} style={{
              display: "flex", gap: 10, alignItems: "center",
              background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
              borderRadius: "var(--cb-radius-sm)", padding: "8px 14px",
            }}>
              <Pill tone="violet">{purpose}</Pill>
              <span className="mono" style={{ fontSize: 12, flex: 1 }}>{model}</span>
              <select
                value={model}
                onChange={(e) => void setRoute(purpose, e.target.value)}
                style={{ fontSize: 11.5, background: "var(--cb-bg3)",
                         border: "1px solid var(--cb-border)",
                         borderRadius: 4, color: "var(--cb-text)", padding: "3px 6px" }}>
              {models.map((m) => (
                <option key={m.alias} value={m.alias}>{m.alias}</option>
              ))}
            </select>
            </div>
            );
          })}
          {Object.keys(routes).length === 0 && (
            <span className="faint" style={{ fontSize: 12 }}>No routes configured.</span>
          )}
        </div>

        {/* Registry */}
        <h2 style={{ fontSize: 13, color: "var(--cb-text-dim)", marginBottom: 10 }}>
          Registry
        </h2>
        <div style={{ display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                      gap: 10 }}>
          {models.map((m) => (
            <div key={m.alias} style={{
              background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
              borderRadius: "var(--cb-radius-md)", padding: 12,
              display: "flex", flexDirection: "column", gap: 6,
            }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className="mono" style={{ fontSize: 12.5, fontWeight: 600,
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap", flex: 1 }}>
                  {m.alias}
                </span>
                <Pill tone={m.locality === "LOCAL" ? "ok" : "info"}>{m.locality}</Pill>
              </div>
              <span className="mono dim" style={{ fontSize: 11 }}>{m.model}</span>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <Pill tone="neutral">{m.provider}</Pill>
                <Pill tone={m.status === "ready" ? "ok" : "warn"}>{m.status}</Pill>
                {m.purpose?.map((p) => (
                  <Pill key={p} tone="violet">{p}</Pill>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
