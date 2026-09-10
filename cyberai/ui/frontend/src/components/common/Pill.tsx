/**
 * Status pill — colored dot + label. Used everywhere for states.
 */

export type PillTone = "ok" | "warn" | "error" | "info" | "neutral" | "violet";

const toneColor: Record<PillTone, string> = {
  ok: "var(--cb-green)",
  warn: "var(--cb-yellow)",
  error: "var(--cb-red)",
  info: "var(--cb-cyan)",
  neutral: "var(--cb-text-faint)",
  violet: "var(--cb-violet)",
};

export function Pill({ tone = "neutral", children, title }: {
  tone?: PillTone; children: React.ReactNode; title?: string;
}) {
  return (
    <span title={title}
          style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            padding: "1px 8px",
            borderRadius: 999,
            border: `1px solid ${toneColor[tone]}44`,
            background: `${toneColor[tone]}14`,
            color: toneColor[tone],
            fontSize: 10.5, fontWeight: 600, letterSpacing: "0.04em",
            whiteSpace: "nowrap",
          }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%",
                     background: toneColor[tone], flexShrink: 0 }} />
      {children}
    </span>
  );
}

/** Map a backend state string to a pill tone. */
export function stateTone(state: string | undefined | null): PillTone {
  switch ((state || "").toUpperCase()) {
    case "ACTIVE": case "ONLINE": case "VERIFIED": case "SUCCESS":
    case "COMPLETED": case "APPROVED": case "LIKELY":
      return "ok";
    case "OFFLINE": case "DEGRADED": case "PENDING": case "UNVERIFIED":
    case "RUNNING": case "SIMULATE":
      return "warn";
    case "UNAUTHORIZED": case "BLOCKED": case "ERROR": case "REJECTED":
    case "DENIED": case "FAILED":
      return "error";
    case "PLAN": case "LAB":
      return "violet";
    default:
      return "neutral";
  }
}
