/**
 * Memory — semantic memory store stats + search.
 * Backed by MemoryManager: GET /memory/stats, GET /memory/search.
 */

import { useState } from "react";
import { memoryApi } from "@/lib/api";
import type { MemorySearchResult } from "@/lib/api";
import { useFetch } from "@/hooks";
import { PageHeader, Spinner, ErrorBox, EmptyState } from "@/components/common/Basics";
import { Pill } from "@/components/common/Pill";

const TYPE_TONE: Record<string, "ok" | "warn" | "error" | "info" | "violet" | "neutral"> = {
  episodic: "info",
  semantic: "violet",
  procedural: "ok",
  tool: "neutral",
  failure: "error",
  experiment: "warn",
};

export function MemoryPage() {
  const stats = useFetch(() => memoryApi.stats(), []);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [results, setResults] = useState<MemorySearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const runSearch = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setSearching(true);
    setSearchError(null);
    try {
      const res = await memoryApi.search(trimmed, 25);
      setResults(res.results);
      setSubmitted(trimmed);
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : "search failed");
      setResults(null);
    } finally {
      setSearching(false);
    }
  };

  if (stats.error) return <ErrorBox error={stats.error} />;
  if (stats.loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <Spinner size={24} />
    </div>
  );

  const total = stats.data?.stats.total ?? 0;
  const byType = stats.data?.stats.by_type ?? {};

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader title="Memory" subtitle={`${total} entries · semantic store`} />
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px" }}>

        {/* Type breakdown */}
        <div style={{
          display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center",
          marginBottom: 18,
        }}>
          {Object.entries(byType).map(([t, n]) => (
            <Pill key={t} tone={TYPE_TONE[t] ?? "neutral"}>
              {t}: {n}
            </Pill>
          ))}
          {Object.keys(byType).length === 0 && (
            <span className="faint" style={{ fontSize: 12 }}>
              Memory store is empty — entries accumulate as missions run.
            </span>
          )}
        </div>

        {/* Search */}
        <form
          onSubmit={(e) => { e.preventDefault(); void runSearch(query); }}
          style={{ display: "flex", gap: 8, marginBottom: 14 }}
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="semantic search — e.g. sql injection findings, recon strategy…"
            style={{
              flex: 1, fontSize: 12.5, padding: "8px 12px",
              background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
              borderRadius: "var(--cb-radius-sm)", color: "var(--cb-text)",
              fontFamily: "var(--cb-font-mono)",
            }}
          />
          <button
            type="submit"
            disabled={searching || !query.trim()}
            style={{
              fontSize: 11, padding: "6px 16px",
              color: "var(--cb-cyan)", border: "1px solid var(--cb-cyan)44",
              borderRadius: 4, background: "transparent",
              cursor: query.trim() ? "pointer" : "default",
            }}
          >
            {searching ? "SEARCHING…" : "SEARCH"}
          </button>
        </form>

        {searchError && <ErrorBox error={searchError} />}

        {/* Results */}
        {results !== null && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span className="faint" style={{ fontSize: 11, marginBottom: 4 }}>
              {results.length} result{results.length === 1 ? "" : "s"} for “{submitted}”
            </span>
            {results.length === 0 && (
              <EmptyState icon="◌" title="No matches"
                           hint="Try broader terms — search falls back to keywords." />
            )}
            {results.map((m) => (
              <div key={m.memory_id} style={{
                background: "var(--cb-bg2)", border: "1px solid var(--cb-border)",
                borderRadius: "var(--cb-radius-sm)", padding: "10px 14px",
              }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center",
                              marginBottom: 4 }}>
                  <Pill tone={TYPE_TONE[m.memory_type] ?? "neutral"}>
                    {m.memory_type}
                  </Pill>
                  {m.similarity !== undefined && (
                    <Pill tone="info">{(m.similarity * 100).toFixed(0)}% match</Pill>
                  )}
                  <Pill tone={m.verification === "VERIFIED" ? "ok" : "warn"}>
                    {m.verification}
                  </Pill>
                  <span className="faint mono" style={{ fontSize: 10, marginLeft: "auto" }}>
                    {m.timestamp}
                  </span>
                </div>
                <div className="dim" style={{ fontSize: 11.5, lineHeight: 1.5 }}>
                  {m.content.length > 400 ? `${m.content.slice(0, 400)}…` : m.content}
                </div>
                <div className="faint mono" style={{ fontSize: 10, marginTop: 4 }}>
                  confidence {m.confidence} · success {m.success_rate} · accessed {m.access_count}×
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
