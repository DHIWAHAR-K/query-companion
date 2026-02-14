import { useEffect, useState } from "react";
import { useChat } from "@/contexts/ChatContext";
import { apiClient, type Connection } from "@/lib/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { Database, Plus } from "lucide-react";

interface ConnectionsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConnectionsSheet({ open, onOpenChange }: ConnectionsSheetProps) {
  const { selectedConnectionId, setSelectedConnectionId } = useChat();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      apiClient
        .getConnections()
        .then(setConnections)
        .catch(() => setConnections([]))
        .finally(() => setLoading(false));
    }
  }, [open]);

  const handleSelect = (id: string | null) => {
    setSelectedConnectionId(id);
    onOpenChange(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-[280px] sm:max-w-[280px]">
        <SheetHeader>
          <SheetTitle>Connections</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-1">
          <button
            type="button"
            onClick={() => handleSelect(null)}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
              selectedConnectionId === null
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent"
            )}
          >
            <Database className="h-4 w-4 shrink-0" />
            <span>Demo</span>
          </button>
          {loading ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">Loading…</p>
          ) : (
            connections.map((conn) => (
              <button
                key={conn.id}
                type="button"
                onClick={() => handleSelect(conn.id)}
                className={cn(
                  "flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                  selectedConnectionId === conn.id
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent"
                )}
              >
                <Database className="h-4 w-4 shrink-0" />
                <span className="truncate">{conn.name}</span>
              </button>
            ))
          )}
          <div className="border-t border-sidebar-border pt-2 mt-2">
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors"
            >
              <Plus className="h-4 w-4 shrink-0" />
              Add connection
            </button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
