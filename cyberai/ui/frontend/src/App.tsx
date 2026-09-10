/**
 * CERBERUS app shell — three-pane layout:
 *   [ActivityBar | Sidebar] [Main view] [Right panel]
 * Dark theme, resizable/collapsible panes, Ctrl+K palette.
 */

import { useEffect, useReducer } from "react";
import { AppContext, initialState, reducer } from "@/stores/app";
import { useApp } from "@/stores/app";
import { useGlobalShortcuts, useLiveEvents, useToast } from "@/hooks";
import { commandsApi } from "@/lib/api";
import { TopBar } from "@/components/layout/TopBar";
import { ActivityBar } from "@/components/layout/ActivityBar";
import { Split } from "@/components/layout/Split";
import { CommandPalette } from "@/components/command/CommandPalette";
import { ChatList } from "@/components/chat/ChatList";
import { RightPanel } from "@/components/layout/RightPanel";
import { Toast } from "@/components/layout/Toast";
import { MainView } from "@/components/layout/MainView";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const ctx = { state, dispatch };

  return (
    <AppContext.Provider value={ctx}>
      <AppShell />
    </AppContext.Provider>
  );
}

/** Inner shell — rendered INSIDE AppContext so hooks can useApp(). */
function AppShell() {
  const { state, dispatch } = useApp();
  useLiveEvents();
  useGlobalShortcuts();
  const toast = useToast();

  // Load the command catalog once (palette + chat autocomplete).
  useEffect(() => {
    commandsApi.catalog()
      .then((c) => dispatch({ type: "SET_COMMANDS", commands: c.commands }))
      .catch(() => toast("error", "failed to load command catalog"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sidebar = (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      background: "var(--cb-bg1)",
    }}>
      <ChatList />
    </div>
  );

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      background: "var(--cb-bg0)", color: "var(--cb-text)",
    }}>
      <TopBar />
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          <ActivityBar />
          <Split
            key={state.sidebarCollapsed ? "sb-collapsed" : "sb-open"}
            first={sidebar}
            second={
              <Split
                key={state.rightPanelCollapsed ? "rp-collapsed" : "rp-open"}
                orientation="vertical"
                initial={state.rightPanelCollapsed ? 0 : 260}
                min={0}
                max={420}
                first={<MainView />}
                second={<RightPanel />}
                onCollapse={() => dispatch({ type: "TOGGLE_RIGHT" })}
              />
            }
            initial={state.sidebarCollapsed ? 0 : 250}
            min={0}
            max={420}
            onCollapse={() => dispatch({ type: "TOGGLE_SIDEBAR" })}
          />
        </div>
      <CommandPalette />
      <Toast />
    </div>
  );
}
