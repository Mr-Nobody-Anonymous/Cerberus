/**
 * Resizable split pane (vertical dividers). Pointer-events based,
 * clamped to min widths, persists nothing (parent owns layout state).
 */

import { useCallback, useEffect, useRef, useState } from "react";

interface SplitProps {
  orientation?: "vertical" | "horizontal";
  initial?: number; // initial first-pane size in px
  min?: number; // min first-pane size
  max?: number; // max first-pane size
  first: React.ReactNode;
  second: React.ReactNode;
  onCollapse?: () => void; // double-click divider
}

export function Split({
  orientation = "vertical", initial = 260, min = 180, max = 480,
  first, second, onCollapse,
}: SplitProps) {
  const [size, setSize] = useState(initial);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    dragging.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    e.preventDefault();
  }, []);

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (!dragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const px = orientation === "vertical" ? e.clientX - rect.left : e.clientY - rect.top;
    setSize(Math.min(max, Math.max(min, px)));
  }, [min, max, orientation]);

  const onPointerUp = useCallback(() => { dragging.current = false; }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [onPointerMove, onPointerUp]);

  const isVertical = orientation === "vertical";

  return (
    <div ref={containerRef}
         style={{ display: "flex", flexDirection: isVertical ? "row" : "column",
                  flex: 1, minHeight: 0, minWidth: 0 }}>
      <div style={{ width: isVertical ? size : undefined,
                    height: isVertical ? undefined : size,
                    minWidth: 0, minHeight: 0, overflow: "hidden",
                    display: "flex", flexDirection: "column" }}>
        {first}
      </div>
      <div
        role="separator"
        aria-orientation={isVertical ? "vertical" : "horizontal"}
        onPointerDown={onPointerDown}
        onDoubleClick={onCollapse}
        style={{
          flexShrink: 0,
          width: isVertical ? 5 : "100%",
          height: isVertical ? "100%" : 5,
          cursor: isVertical ? "col-resize" : "row-resize",
          background: "var(--cb-border)",
          transition: "background 120ms",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--cb-cyan)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "var(--cb-border)")}
      />
      <div style={{ flex: 1, minWidth: 0, minHeight: 0, overflow: "hidden",
                    display: "flex", flexDirection: "column" }}>
        {second}
      </div>
    </div>
  );
}
