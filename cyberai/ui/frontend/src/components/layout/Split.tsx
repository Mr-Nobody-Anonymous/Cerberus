/**
 * Resizable split pane (vertical dividers). Pointer-events based,
 * clamped to min widths, persists nothing (parent owns layout state).
 *
 * `reverse` sizes the SECOND pane instead of the first (for right-side
 * panels): the divider then controls the second pane's width, measured
 * from the container's right edge.
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
  /** Size the second pane instead of the first (right-side panels). */
  reverse?: boolean;
  /** Collapse the sized pane entirely (parent-controlled). */
  collapsed?: boolean;
}

export function Split({
  orientation = "vertical", initial = 260, min = 180, max = 480,
  first, second, onCollapse, reverse = false, collapsed = false,
}: SplitProps) {
  const [size, setSize] = useState(initial);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    dragging.current = true;
    try {
      // Keep receiving moves even if the pointer leaves the window.
      // Best-effort: the window-level listeners below drive the drag anyway.
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      /* synthetic / inactive pointers cannot be captured — ignore */
    }
    e.preventDefault();
  }, []);

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (!dragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    let px = orientation === "vertical" ? e.clientX - rect.left : e.clientY - rect.top;
    if (reverse) px = (orientation === "vertical" ? rect.right : rect.bottom) - px;
    setSize(Math.min(max, Math.max(min, px)));
  }, [min, max, orientation, reverse]);

  const onPointerUp = useCallback(() => { dragging.current = false; }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
    };
  }, [onPointerMove, onPointerUp]);

  const isVertical = orientation === "vertical";
  const sized = collapsed ? 0 : size;
  const sizedStyle = {
    width: isVertical ? sized : undefined,
    height: isVertical ? undefined : sized,
    minWidth: 0, minHeight: 0, overflow: "hidden",
    display: "flex", flexDirection: "column" as const,
  };
  const fillStyle = {
    flex: 1, minWidth: 0, minHeight: 0, overflow: "hidden",
    display: "flex", flexDirection: "column" as const,
  };

  return (
    <div ref={containerRef}
         style={{ display: "flex", flexDirection: isVertical ? "row" : "column",
                  flex: 1, minHeight: 0, minWidth: 0 }}>
      {reverse ? (
        <>
          <div style={fillStyle}>{first}</div>
          {!collapsed && (
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
          )}
          <div style={sizedStyle}>{second}</div>
        </>
      ) : (
        <>
          <div style={sizedStyle}>{first}</div>
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
          <div style={fillStyle}>{second}</div>
        </>
      )}
    </div>
  );
}
