import { useAuth } from "@/contexts/AuthContext";
import { useChat } from "@/contexts/ChatContext";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  PanelLeftClose,
  Plus,
  Search,
  FolderOpen,
  LayoutGrid,
  Code,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { user } = useAuth();
  const { createChat } = useChat();

  return (
    <div className="flex h-full w-[52px] flex-col items-center bg-sidebar py-3 gap-1">
      {/* Top icons */}
      <button
        onClick={onToggle}
        className="flex items-center justify-center h-9 w-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors"
      >
        <PanelLeftClose className="h-[18px] w-[18px]" />
      </button>

      <button
        onClick={createChat}
        className="flex items-center justify-center h-9 w-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors"
      >
        <Plus className="h-[18px] w-[18px]" />
      </button>

      <button className="flex items-center justify-center h-9 w-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
        <Search className="h-[18px] w-[18px]" />
      </button>

      <button className="flex items-center justify-center h-9 w-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
        <FolderOpen className="h-[18px] w-[18px]" />
      </button>

      <button className="flex items-center justify-center h-9 w-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
        <LayoutGrid className="h-[18px] w-[18px]" />
      </button>

      <button className="flex items-center justify-center h-9 w-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
        <Code className="h-[18px] w-[18px]" />
      </button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* User avatar */}
      <Avatar className="h-8 w-8 cursor-pointer">
        <AvatarFallback className="text-[11px] font-semibold bg-primary text-primary-foreground">
          {user?.name?.slice(0, 2).toUpperCase() || "DA"}
        </AvatarFallback>
      </Avatar>
    </div>
  );
}
