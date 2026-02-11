import { useAuth } from "@/contexts/AuthContext";
import { useChat, type Mode } from "@/contexts/ChatContext";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  PanelLeftClose,
  PanelLeft,
  Plus,
  Search,
  FolderOpen,
  LayoutGrid,
  Code,
  MessageSquare,
  MoreHorizontal,
  Trash2,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

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
  const { chats, activeChat, createChat, selectChat, deleteChat } = useChat();
  const groups = groupChatsByDate(chats);

  const iconBtn =
    "flex items-center justify-center h-9 w-9 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors shrink-0";

  if (collapsed) {
    return (
      <div className="flex h-full w-[52px] flex-col items-center bg-sidebar py-3 gap-1">
        <button onClick={onToggle} className={iconBtn}>
          <PanelLeft className="h-[18px] w-[18px]" />
        </button>
        <button onClick={createChat} className={iconBtn}>
          <Plus className="h-[18px] w-[18px]" />
        </button>
        <button className={iconBtn}><Search className="h-[18px] w-[18px]" /></button>
        <button className={iconBtn}><FolderOpen className="h-[18px] w-[18px]" /></button>
        <button className={iconBtn}><LayoutGrid className="h-[18px] w-[18px]" /></button>
        <button className={iconBtn}><Code className="h-[18px] w-[18px]" /></button>
        <div className="flex-1" />
        <Avatar className="h-8 w-8 cursor-pointer" onClick={onToggle}>
          <AvatarFallback className="text-[11px] font-semibold bg-primary text-primary-foreground">
            {user?.full_name?.slice(0, 2).toUpperCase() || "DA"}
          </AvatarFallback>
        </Avatar>
      </div>
    );
  }

  return (
    <div className="flex h-full w-[260px] flex-col bg-sidebar transition-all">
      {/* Top bar */}
      <div className="flex items-center justify-between px-3 pt-3 pb-1">
        <button onClick={onToggle} className={iconBtn}>
          <PanelLeftClose className="h-[18px] w-[18px]" />
        </button>
        <button onClick={createChat} className={iconBtn}>
          <Plus className="h-[18px] w-[18px]" />
        </button>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto px-2 pt-2">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <p className="px-2 py-1 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              {group.label}
            </p>
            {group.chats.map((chat) => (
              <div
                key={chat.id}
                className={cn(
                  "group flex items-center gap-2 rounded-lg px-2 py-1.5 cursor-pointer text-sm hover:bg-sidebar-accent transition-colors",
                  activeChat?.id === chat.id && "bg-sidebar-accent"
                )}
                onClick={() => selectChat(chat.id)}
              >
                <span className="flex-1 truncate text-sidebar-foreground text-[13px]">{chat.title}</span>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-accent rounded transition-opacity">
                      <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-36">
                    <DropdownMenuItem
                      onClick={(e) => { e.stopPropagation(); deleteChat(chat.id); }}
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

      {/* Bottom */}
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-[11px] font-semibold bg-primary text-primary-foreground">
              {user?.full_name?.slice(0, 2).toUpperCase() || "DA"}
            </AvatarFallback>
          </Avatar>
          <span className="flex-1 truncate text-sm text-sidebar-foreground">{user?.full_name}</span>
          <button onClick={logout} className={cn(iconBtn, "h-7 w-7")}>
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
