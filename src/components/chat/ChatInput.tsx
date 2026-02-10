import { useState, useRef, useEffect } from "react";
import { useChat, type Mode } from "@/contexts/ChatContext";
import { Plus, ArrowUp, Volume2, Pencil, GraduationCap, Code, Sparkles, HardDrive } from "lucide-react";

const modeLabels: Record<Mode, string> = {
  valtryek: "Valtryek",
  achillies: "Achillies",
  spryzen: "Spryzen",
};

const quickActions = [
  { label: "Write", icon: Pencil },
  { label: "Learn", icon: GraduationCap },
  { label: "Code", icon: Code },
  { label: "Life stuff", icon: Sparkles },
  { label: "From Drive", icon: HardDrive },
];

export default function ChatInput() {
  const { sendMessage, mode } = useChat();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { activeChat } = useChat();

  const hasMessages = activeChat && activeChat.messages.length > 0;

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
    <div className="mx-auto w-full max-w-[600px] px-4 pb-4">
      {/* Input box */}
      <div className="rounded-2xl border border-border bg-surface overflow-hidden">
        {/* Textarea row */}
        <div className="px-4 pt-3 pb-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="How can I help you today?"
            rows={1}
            className="w-full resize-none bg-transparent text-[15px] text-foreground placeholder:text-muted-foreground focus:outline-none min-h-[24px] max-h-[200px]"
          />
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          <button className="flex items-center justify-center h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
            <Plus className="h-4 w-4" />
          </button>

          <div className="flex items-center gap-2">
            {/* Model selector */}
            <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <span className="font-medium text-foreground">{modeLabels[mode]}</span>
              <span className="text-muted-foreground">Extended</span>
              <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none">
                <path d="M3 5L6 8L9 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

            {/* Audio / Send */}
            {value.trim() ? (
              <button
                onClick={handleSubmit}
                className="flex items-center justify-center h-8 w-8 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            ) : (
              <button className="flex items-center justify-center h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                <Volume2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Quick action pills – only show on empty state */}
      {!hasMessages && (
        <div className="flex items-center justify-center gap-2 mt-3 flex-wrap">
          {quickActions.map((action) => (
            <button
              key={action.label}
              className="flex items-center gap-1.5 rounded-full border border-border bg-transparent px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              <action.icon className="h-3.5 w-3.5" />
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
