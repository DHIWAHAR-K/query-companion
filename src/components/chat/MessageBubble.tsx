import { useState } from "react";
import type { Message } from "@/contexts/ChatContext";
import { cn } from "@/lib/utils";
import { Copy, ThumbsUp, ThumbsDown, RotateCcw, Check } from "lucide-react";

export default function MessageBubble({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] rounded-3xl bg-surface px-4 py-2.5">
          <p className="text-[15px] text-foreground whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  if (message.role === "system") {
    return (
      <div className="rounded-xl border border-border bg-surface/50 px-4 py-2.5 text-sm text-muted-foreground">
        {message.content}
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex flex-col gap-1 max-w-[85%]">
      {/* Content */}
      <div className="text-[15px] text-foreground whitespace-pre-wrap leading-relaxed">
        {message.content}
        {message.isStreaming && !message.content && (
          <span className="inline-block text-xl animate-pulse">✸</span>
        )}
        {message.isStreaming && message.content && (
          <span className="inline-block w-1.5 h-4 bg-foreground/70 ml-0.5 animate-pulse align-text-bottom" />
        )}
      </div>

      {/* Action icons - only show when not streaming and has content */}
      {!message.isStreaming && message.content && (
        <div className="flex items-center gap-1 mt-1">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md text-muted-foreground/50 hover:text-muted-foreground hover:bg-accent transition-colors"
            title="Copy"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
          <button
            className="p-1.5 rounded-md text-muted-foreground/50 hover:text-muted-foreground hover:bg-accent transition-colors"
            title="Good response"
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </button>
          <button
            className="p-1.5 rounded-md text-muted-foreground/50 hover:text-muted-foreground hover:bg-accent transition-colors"
            title="Bad response"
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </button>
          <button
            className="p-1.5 rounded-md text-muted-foreground/50 hover:text-muted-foreground hover:bg-accent transition-colors"
            title="Retry"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
