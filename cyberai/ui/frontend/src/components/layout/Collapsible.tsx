/**
 * Collapsible panel wrapper with header + optional collapse toggle.
 */

import { useState } from "react";

interface CollapsibleProps {
  title: string;
  defaultOpen?: boolean;
  right?: React.ReactNode;
  children: React.ReactNode;
}

export function Collapsible({ title, defaultOpen = true, right, children }: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section style={{ borderBottom: "1px solid var(--cb-border)" }}>
      <header
        onClick={() => setOpen(!open)}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "8px 12px", cursor: "pointer",
          userSelect: "none",
          color: "var(--cb-text-dim)",
          fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em",
        }}>
        <span style={{
          display: "inline-block", transition: "transform 150ms",
          transform: open ? "rotate(90deg)" : "rotate(0deg)",
          fontSize: 9,
        }}>▶</span>
        <span style={{ flex: 1 }}>{title}</span>
        {right}
      </header>
      {open && <div style={{ padding: "0 12px 10px" }}>{children}</div>}
    </section>
  );
}
