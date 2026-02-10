import { useRef, useEffect } from "react";
import { useChat } from "@/contexts/ChatContext";
import { useAuth } from "@/contexts/AuthContext";
import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function ChatPane() {
  const { activeChat } = useChat();
  const { user } = useAuth();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activeChat?.messages]);

  const hasMessages = activeChat && activeChat.messages.length > 0;

  return (
    <div className="flex flex-1 flex-col min-w-0 bg-background">
      {hasMessages ? (
        <>
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-[768px] px-4 py-6 space-y-6">
              {activeChat.messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </div>
          </div>
          <ChatInput />
        </>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-4">
          {/* Plan badge */}
          <div className="mb-6">
            <span className="text-xs text-muted-foreground border border-border rounded-full px-3 py-1">
              Free plan · <span className="text-foreground cursor-pointer hover:underline">Upgrade</span>
            </span>
          </div>

          {/* Greeting */}
          <h1 className="text-3xl font-medium text-foreground mb-8">
            <span className="mr-2">✸</span>
            {getGreeting()}, {user?.name?.split(" ")[0] || "there"}
          </h1>

          {/* Input area */}
          <ChatInput />
        </div>
      )}
    </div>
  );
}
