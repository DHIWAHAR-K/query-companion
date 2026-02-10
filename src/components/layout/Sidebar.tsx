import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useChat, type Mode } from "@/contexts/ChatContext";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Database,
  Plus,
  MessageSquare,
  Settings,
  LogOut,
  MoreHorizontal,
  Trash2,
  ChevronLeft,
  Zap,
  Shield,
  Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const modeConfig: Record<Mode, { label: string; icon: React.ReactNode; color: string }> = {
  valtryek: { label: "Valtryek", icon: <Zap className="h-3 w-3" />, color: "text-warning" },
  achillies: { label: "Achillies", icon: <Shield className="h-3 w-3" />, color: "text-primary" },
  spryzen: { label: "Spryzen", icon: <Brain className="h-3 w-3" />, color: "text-success" },
};

function groupChatsByDate(chats: { id: string; title: string; updatedAt: Date }[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const last7 = new Date(today.getTime() - 7 * 86400000);
  const last30 = new Date(today.getTime() - 30 * 86400000);

  const groups: { label: string; chats: typeof chats }[] = [
    { label: "Today", chats: [] },
    { label: "Yesterday", chats: [] },
    { label: "Last 7 days", chats: [] },
    { label: "Last 30 days", chats: [] },
    { label: "Older", chats: [] },
  ];

  for (const chat of chats) {
    const d = new Date(chat.updatedAt);
    if (d >= today) groups[0].chats.push(chat);
    else if (d >= yesterday) groups[1].chats.push(chat);
    else if (d >= last7) groups[2].chats.push(chat);
    else if (d >= last30) groups[3].chats.push(chat);
    else groups[4].chats.push(chat);
  }

  return groups.filter((g) => g.chats.length > 0);
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { user, logout } = useAuth();
  const { chats, activeChat, mode, createChat, selectChat, deleteChat } = useChat();

  const groups = groupChatsByDate(chats);

  if (collapsed) {
    return (
      <div className="flex h-full w-[60px] flex-col items-center border-r border-sidebar-border bg-sidebar py-3 gap-2">
        <Button variant="ghost" size="icon" onClick={onToggle} className="mb-2">
          <Database className="h-5 w-5 text-primary" />
        </Button>
        <Button variant="ghost" size="icon" onClick={createChat}>
          <Plus className="h-5 w-5" />
        </Button>
        <div className="flex-1" />
        <Avatar className="h-8 w-8 cursor-pointer" onClick={onToggle}>
          <AvatarFallback className="text-xs bg-primary text-primary-foreground">
            {user?.name?.[0]?.toUpperCase() || "U"}
          </AvatarFallback>
        </Avatar>
      </div>
    );
  }

  return (
    <div className="flex h-full w-[260px] flex-col border-r border-sidebar-border bg-sidebar">
      {/* Header */}
      <div className="flex items-center justify-between p-3 pb-2">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm text-sidebar-foreground">Queryus</span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggle}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </div>

      {/* New Chat */}
      <div className="px-3 pb-2">
        <Button
          onClick={createChat}
          variant="outline"
          className="w-full justify-start gap-2 text-sm h-9"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Connection selector */}
      <div className="px-3 pb-3">
        <div className="flex items-center gap-2 rounded-md border border-sidebar-border px-2.5 py-1.5 text-xs text-muted-foreground">
          <Database className="h-3 w-3" />
          <span className="truncate">Production DB</span>
        </div>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto px-1.5">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <p className="px-2 py-1 text-xs font-medium text-muted-foreground">{group.label}</p>
            {group.chats.map((chat) => (
              <div
                key={chat.id}
                className={cn(
                  "group flex items-center gap-2 rounded-lg px-2 py-1.5 cursor-pointer text-sm hover:bg-sidebar-accent transition-colors",
                  activeChat?.id === chat.id && "bg-sidebar-accent"
                )}
                onClick={() => selectChat(chat.id)}
              >
                <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="flex-1 truncate text-sidebar-foreground">{chat.title}</span>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-accent rounded transition-opacity">
                      <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-36">
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteChat(chat.id);
                      }}
                      className="text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Bottom section */}
      <div className="border-t border-sidebar-border p-3 space-y-2">
        {/* Mode indicator */}
        <div className={cn("flex items-center gap-1.5 text-xs", modeConfig[mode].color)}>
          {modeConfig[mode].icon}
          <span className="font-medium">{modeConfig[mode].label}</span>
          <span className="text-muted-foreground">mode</span>
        </div>

        {/* User */}
        <div className="flex items-center gap-2">
          <Avatar className="h-7 w-7">
            <AvatarFallback className="text-xs bg-primary text-primary-foreground">
              {user?.name?.[0]?.toUpperCase() || "U"}
            </AvatarFallback>
          </Avatar>
          <span className="flex-1 truncate text-sm text-sidebar-foreground">{user?.name}</span>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={logout}>
            <LogOut className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
