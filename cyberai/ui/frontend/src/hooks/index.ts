/**
 * Shared hooks: SSE subscription, fetch helpers, keyboard shortcuts.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { subscribeEvents } from "@/lib/api";
import type { EventDto } from "@/lib/api";
import { useApp } from "@/stores/app";

/** Subscribe to the live SSE event stream for the app lifetime. */
export function useLiveEvents(): void {
  const { dispatch } = useApp();
  useEffect(() => {
    const dispose = subscribeEvents(
      (ev: EventDto) => dispatch({ type: "EVENT", event: ev }),
      (up: boolean) => dispatch({ type: "SSE_STATUS", up }),
    );
    return dispose;
  }, [dispatch]);
}

/** Fetch + cache helper with refresh. */
export function useFetch<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fetcherRef.current());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return { data, error, loading, refresh };
}

/** Global keyboard shortcuts: Ctrl+K palette, Ctrl+B sidebar, Ctrl+J right panel. */
export function useGlobalShortcuts(): void {
  const { dispatch, state } = useApp();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const k = e.key.toLowerCase();
      if (k === "k") {
        e.preventDefault();
        dispatch({ type: "PALETTE_OPEN", open: !state.paletteOpen });
      } else if (k === "b") {
        e.preventDefault();
        dispatch({ type: "TOGGLE_SIDEBAR" });
      } else if (k === "j") {
        e.preventDefault();
        dispatch({ type: "TOGGLE_RIGHT" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dispatch, state.paletteOpen]);
}

/** Auto-clearing toast. */
export function useToast() {
  const { dispatch } = useApp();
  const timer = useRef<number | undefined>(undefined);
  const show = useCallback((kind: "info" | "success" | "error", text: string) => {
    dispatch({ type: "TOAST", kind, text });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => dispatch({ type: "TOAST_CLEAR" }), 3500);
  }, [dispatch]);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  return show;
}
