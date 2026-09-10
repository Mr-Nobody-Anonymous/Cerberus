/**
 * Shared small components: Spinner, EmptyState, ErrorBox, Badge, IconButton.
 */

export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <span style={{
      display: "inline-block", width: size, height: size,
      border: "2px solid var(--cb-border-bright)",
      borderTopColor: "var(--cb-cyan)",
      borderRadius: "50%",
      animation: "cb-spin 700ms linear infinite",
    }} />
  );
}

export function EmptyState({ icon = "◇", title, hint }: {
  icon?: string; title: string; hint?: string;
}) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", gap: 6, padding: "40px 20px",
      color: "var(--cb-text-faint)", textAlign: "center", height: "100%",
    }}>
      <div style={{ fontSize: 28, opacity: 0.5 }}>{icon}</div>
      <div style={{ fontSize: 13, color: "var(--cb-text-dim)" }}>{title}</div>
      {hint && <div style={{ fontSize: 11.5, maxWidth: 320 }}>{hint}</div>}
    </div>
  );
}

export function ErrorBox({ error }: { error: string }) {
  return (
    <div style={{
      padding: "10px 14px", margin: "10px 12px",
      border: "1px solid var(--cb-red)55", borderRadius: "var(--cb-radius-md)",
      background: "var(--cb-red)12", color: "var(--cb-red)",
      fontSize: 12, fontFamily: "var(--cb-font-mono)",
      overflowWrap: "anywhere",
    }}>
      ⚠ {error}
    </div>
  );
}

export function Badge({ children, tone = "neutral" }: {
  children: React.ReactNode; tone?: "cyan" | "violet" | "green" | "yellow" | "red" | "neutral";
}) {
  const color = tone === "neutral" ? "var(--cb-text-dim)"
    : `var(--cb-${tone === "cyan" ? "cyan" : tone})`;
  return (
    <span style={{
      padding: "0 6px", borderRadius: 4,
      background: "var(--cb-bg3)", color,
      fontSize: 10.5, fontFamily: "var(--cb-font-mono)",
      border: `1px solid ${color}33`,
    }}>{children}</span>
  );
}

export function IconButton({ title, onClick, children, danger }: {
  title: string; onClick?: () => void; children: React.ReactNode; danger?: boolean;
}) {
  return (
    <button title={title} onClick={onClick}
            style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: 24, height: 24, borderRadius: "var(--cb-radius-sm)",
              color: danger ? "var(--cb-red)" : "var(--cb-text-dim)",
              fontSize: 13,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--cb-bg3)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "none")}>
      {children}
    </button>
  );
}

/** Page header used by every main view. */
export function PageHeader({ title, subtitle, actions }: {
  title: string; subtitle?: string; actions?: React.ReactNode;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 12,
      padding: "14px 18px", borderBottom: "1px solid var(--cb-border)",
      flexShrink: 0,
    }}>
      <h1 style={{ fontSize: 16, fontWeight: 600, letterSpacing: "0.02em" }}>{title}</h1>
      {subtitle && <span className="dim" style={{ fontSize: 12 }}>{subtitle}</span>}
      <div style={{ flex: 1 }} />
      {actions}
    </div>
  );
}
