import { useRef, useEffect } from "react";
import { useChat, type Mode } from "@/contexts/ChatContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Share2, Zap, Shield, Brain, Database } from "lucide-react";
import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";

const modes: { key: Mode; label: string; icon: React.ReactNode }[] = [
  { key: "valtryek", label: "Valtryek", icon: <Zap className="h-3.5 w-3.5" /> },
  { key: "achillies", label: "Achillies", icon: <Shield className="h-3.5 w-3.5" /> },
  { key: "spryzen", label: "Spryzen", icon: <Brain className="h-3.5 w-3.5" /> },
];

export default function ChatPane() {
  const { activeChat, mode, setMode } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activeChat?.messages]);

  return (
    <div className="flex flex-1 flex-col min-w-0 bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-[52px] shrink-0">
        <h2 className="text-sm font-medium text-foreground truncate">
          {activeChat?.title || "New conversation"}
        </h2>
        <div className="flex items-center gap-2">
          {/* Mode switcher */}
          <div className="flex items-center rounded-lg bg-surface p-0.5">
            {modes.map((m) => (
              <button
                key={m.key}
                onClick={() => setMode(m.key)}
                className={cn(
                  "flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-all",
                  mode === m.key
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {m.icon}
                {m.label}
              </button>
            ))}
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Share2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[768px] px-4 py-6 space-y-6">
          {(!activeChat || activeChat.messages.length === 0) && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <Database className="h-10 w-10 text-muted-foreground/40 mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-1">What can I help you query?</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Ask me anything about your data. I'll generate SQL, execute queries, and visualize results.
              </p>
            </div>
          )}
          {activeChat?.messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
        </div>
      </div>

      {/* Input */}
      <ChatInput />
    </div>
  );
}
