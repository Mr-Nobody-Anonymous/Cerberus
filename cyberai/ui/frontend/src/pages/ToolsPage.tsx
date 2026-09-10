/**
 * Tools — registry + adapter presence + health.
 */

import { toolsApi } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

export function ToolsPage() {
  const toast = useToast();
  const { data, loading, error, refresh } = useFetch(() => toolsApi.list(), []);

  const runHealth = async (name: string) => {
    try {
      const res = await toolsApi.health(name);
      const health = (res as { health?: string }).health ?? "unknown";
      toast(health === "healthy" ? "success" : "info",
            health === "healthy" ? `✓ ${name}: healthy` : `${name}: ${health}`);
      await refresh();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "health check failed");
    }
  };

  if (error) return <ErrorBox error={error} />;
  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const tools = data?.tools ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Tools" subtitle={`${tools.length} registered`}
                  actions={
                    <span className="faint" style={{ fontSize: 10.5 }}>
                      per-tool health via GET /tools/&#123;name&#125;
                    </span>
                  } />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>
        {tools.length === 0 && (
          <EmptyState icon="⚒" title="No tools registered"
                       hint="Adapters register tools when discovered." />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {tools.map((t) => (
            <div key={t.name} style={{
              display: "flex", gap: 10, alignItems: "center",
              background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
              borderRadius: "var(--cb-radius-sm)", padding: "9px 14px",
            }}>
              <span className="mono" style={{ fontSize: 12.5, fontWeight: 600,
                                              color: "var(--cb-cyan)" }}>
                {t.name}
              </span>
              <span className="dim" style={{ fontSize: 11.5, flex: 1,
                                             overflow: "hidden",
                                             textOverflow: "ellipsis",
                                             whiteSpace: "nowrap" }}>
                {t.description}
              </span>
              {t.category && <Pill tone="violet">{t.category}</Pill>}
              <button onClick={() => void runHealth(t.name)}
                      style={{ fontSize: 10, padding: "2px 10px",
                               color: "var(--cb-cyan)",
                               border: "1px solid var(--cb-cyan)44", borderRadius: 4,
                               background: "transparent" }}>
                HEALTH
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
