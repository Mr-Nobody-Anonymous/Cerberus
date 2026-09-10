/**
 * Global app state — React context + reducer. No external state library.
 *
 * Holds: active view, active chat/session, live event stream status,
 * command palette visibility, and the command catalog (for palette +
 * chat autocomplete).
 */

import { createContext, useContext } from "react";
import type { CommandCatalogEntry, EventDto } from "@/lib/api";

export type ViewId =
  | "dashboard"
  | "chat"
  | "missions"
  | "findings"
  | "targets"
  | "agents"
  | "tools"
  | "models"
  | "security"
  | "memory"
  | "evidence"
  | "sessions"
  | "workspace"
  | "events";

export interface AppState {
  view: ViewId;
  activeChatId: string | null;
  activeSessionId: string | null;
  paletteOpen: boolean;
  paletteQuery: string;
  sseUp: boolean | null; // null = connecting, true/false = status
  events: EventDto[]; // ring buffer of recent live events
  commands: CommandCatalogEntry[];
  sidebarCollapsed: boolean;
  rightPanelCollapsed: boolean;
  toast: { kind: "info" | "success" | "error"; text: string } | null;
}

export const initialState: AppState = {
  view: "chat",
  activeChatId: null,
  activeSessionId: null,
  paletteOpen: false,
  paletteQuery: "",
  sseUp: null,
  events: [],
  commands: [],
  sidebarCollapsed: false,
  rightPanelCollapsed: false,
  toast: null,
};

export type Action =
  | { type: "SET_VIEW"; view: ViewId }
  | { type: "SET_ACTIVE_CHAT"; id: string | null }
  | { type: "SET_ACTIVE_SESSION"; id: string | null }
  | { type: "PALETTE_OPEN"; open: boolean; query?: string }
  | { type: "SSE_STATUS"; up: boolean }
  | { type: "EVENT"; event: EventDto }
  | { type: "SET_COMMANDS"; commands: CommandCatalogEntry[] }
  | { type: "TOGGLE_SIDEBAR" }
  | { type: "TOGGLE_RIGHT" }
  | { type: "TOAST"; kind: "info" | "success" | "error"; text: string }
  | { type: "TOAST_CLEAR" };

export const EVENT_RING_MAX = 300;

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_VIEW":
      return { ...state, view: action.view };
    case "SET_ACTIVE_CHAT":
      return { ...state, activeChatId: action.id, view: action.id ? "chat" : state.view };
    case "SET_ACTIVE_SESSION":
      return { ...state, activeSessionId: action.id };
    case "PALETTE_OPEN":
      return { ...state, paletteOpen: action.open,
               paletteQuery: action.query ?? (action.open ? "" : state.paletteQuery) };
    case "SSE_STATUS":
      return { ...state, sseUp: action.up };
    case "EVENT": {
      const events = [action.event, ...state.events].slice(0, EVENT_RING_MAX);
      return { ...state, events };
    }
    case "SET_COMMANDS":
      return { ...state, commands: action.commands };
    case "TOGGLE_SIDEBAR":
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed };
    case "TOGGLE_RIGHT":
      return { ...state, rightPanelCollapsed: !state.rightPanelCollapsed };
    case "TOAST":
      return { ...state, toast: { kind: action.kind, text: action.text } };
    case "TOAST_CLEAR":
      return { ...state, toast: null };
    default:
      return state;
  }
}

export interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<Action>;
}

export const AppContext = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
