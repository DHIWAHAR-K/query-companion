import { useState, useRef, useEffect } from "react";
import { useChat } from "@/contexts/ChatContext";
import { Button } from "@/components/ui/button";
import { Paperclip, ArrowUp } from "lucide-react";

export default function ChatInput() {
  const { sendMessage } = useChat();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    sendMessage(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="mx-auto w-full max-w-[768px] px-4 pb-4">
      <div className="relative flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-sm">
        <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0 text-muted-foreground">
          <Paperclip className="h-4 w-4" />
        </Button>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your data..."
          rows={1}
          className="flex-1 resize-none bg-transparent text-message text-foreground placeholder:text-muted-foreground focus:outline-none min-h-[24px] max-h-[200px] py-1"
        />
        <Button
          size="icon"
          className="h-8 w-8 shrink-0 rounded-lg"
          disabled={!value.trim()}
          onClick={handleSubmit}
        >
          <ArrowUp className="h-4 w-4" />
        </Button>
      </div>
      <p className="text-center text-[11px] text-muted-foreground mt-2">
        Queryus can make mistakes. Verify SQL before execution.
      </p>
    </div>
  );
}
