/**
 * Main view router — renders the active page.
 */

import { useApp } from "@/stores/app";
import { ChatView } from "@/components/chat/ChatView";
import { DashboardPage } from "@/pages/DashboardPage";
import { MissionsPage } from "@/pages/MissionsPage";
import { FindingsPage } from "@/pages/FindingsPage";
import { TargetsPage } from "@/pages/TargetsPage";
import { AgentsPage } from "@/pages/AgentsPage";
import { ToolsPage } from "@/pages/ToolsPage";
import { ModelsPage } from "@/pages/ModelsPage";
import { SecurityPage } from "@/pages/SecurityPage";
import { MemoryPage } from "@/pages/MemoryPage";
import { EvidencePage } from "@/pages/EvidencePage";
import { SessionsPage } from "@/pages/SessionsPage";
import { WorkspacePage } from "@/pages/WorkspacePage";
import { EventsPage } from "@/pages/EventsPage";

export function MainView() {
  const { state } = useApp();
  switch (state.view) {
    case "chat": return <ChatView />;
    case "dashboard": return <DashboardPage />;
    case "missions": return <MissionsPage />;
    case "findings": return <FindingsPage />;
    case "targets": return <TargetsPage />;
    case "agents": return <AgentsPage />;
    case "tools": return <ToolsPage />;
    case "models": return <ModelsPage />;
    case "security": return <SecurityPage />;
    case "memory": return <MemoryPage />;
    case "evidence": return <EvidencePage />;
    case "sessions": return <SessionsPage />;
    case "workspace": return <WorkspacePage />;
    case "events": return <EventsPage />;
    default: return <ChatView />;
  }
}
