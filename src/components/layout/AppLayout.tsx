import { useState } from "react";
import Sidebar from "./Sidebar";
import ChatPane from "@/components/chat/ChatPane";

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <ChatPane />
    </div>
  );
}
