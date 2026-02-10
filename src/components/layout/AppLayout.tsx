import { useState } from "react";
import Sidebar from "./Sidebar";
import RightPanel from "./RightPanel";
import ChatPane from "@/components/chat/ChatPane";
import { useIsMobile } from "@/hooks/use-mobile";

export default function AppLayout() {
  const isMobile = useIsMobile();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(!isMobile);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <ChatPane />
      {rightPanelOpen && !isMobile && <RightPanel onClose={() => setRightPanelOpen(false)} />}
    </div>
  );
}
