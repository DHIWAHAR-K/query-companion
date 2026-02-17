import { useState, useRef, useEffect } from "react";
import { useChat, type Mode } from "@/contexts/ChatContext";
import { Paperclip, ArrowUp, Volume2, Pencil, GraduationCap, Code, Sparkles, HardDrive, X } from "lucide-react";

const modeLabels: Record<Mode, string> = {
  valtryek: "Valtryek",
  achillies: "Achillies",
  spryzen: "Spryzen",
};

const DATA_FILE_EXTENSIONS = [".csv", ".tsv"];
function isDataFile(filename: string): boolean {
  const lower = filename.toLowerCase();
  return DATA_FILE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export type AttachmentForSend = {
  type: "file";
  data: string;
  filename: string;
};

const quickActions = [
  { label: "Write", icon: Pencil },
  { label: "Learn", icon: GraduationCap },
  { label: "Code", icon: Code },
  { label: "Life stuff", icon: Sparkles },
  { label: "From Drive", icon: HardDrive },
];

export default function ChatInput() {
  const { sendMessage, mode, activeChat } = useChat();
  const [value, setValue] = useState("");
  const [attachedFile, setAttachedFile] = useState<AttachmentForSend | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const hasMessages = activeChat && activeChat.messages.length > 0;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!isDataFile(file.name)) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = typeof reader.result === "string" ? reader.result.split(",")[1] ?? reader.result : null;
      if (b64) {
        setAttachedFile({ type: "file", data: b64, filename: file.name });
      }
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    const attachments = attachedFile ? [attachedFile] : undefined;
    sendMessage(trimmed, attachments);
    setValue("");
    setAttachedFile(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="mx-auto w-full max-w-[600px] px-4 pb-4">
      <div className="rounded-2xl border border-border bg-surface overflow-hidden">
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

        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          <div className="flex items-center gap-1">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.tsv"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center justify-center h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              title="Attach CSV/TSV file"
            >
              <Paperclip className="h-4 w-4" />
            </button>
            {attachedFile && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground max-w-[180px] truncate">
                <span className="truncate">{attachedFile.filename}</span>
                <button
                  type="button"
                  onClick={() => setAttachedFile(null)}
                  className="p-0.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
                  aria-label="Remove attachment"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <span className="font-medium text-foreground">{modeLabels[mode]}</span>
              <span className="text-muted-foreground">Extended</span>
              <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none">
                <path d="M3 5L6 8L9 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

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

      {!hasMessages && (
        <div className="flex items-center justify-center gap-2 mt-3 flex-wrap">
          {quickActions.map((action) => (
            <button
              key={action.label}
              type="button"
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
