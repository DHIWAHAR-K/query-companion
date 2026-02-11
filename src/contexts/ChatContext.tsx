import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { useAuth } from "./AuthContext";

export type ToolEvent = {
  id: string;
  label: string;
  icon: string;
  durationMs: number;
  details?: string;
};

export type SQLBlock = {
  query: string;
  dialect: string;
};

export type QueryResult = {
  columns: { name: string; type: string }[];
  rows: any[][];
  totalRows: number;
  executionTimeMs: number;
};

export type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  toolEvents?: ToolEvent[];
  sql?: SQLBlock;
  results?: QueryResult;
  isStreaming?: boolean;
};

export type Chat = {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
};

export type Mode = "valtryek" | "achillies" | "spryzen";

type ChatContextType = {
  chats: Chat[];
  activeChat: Chat | null;
  mode: Mode;
  isLoading: boolean;
  activeConnectionId: string | null;
  connections: any[];
  setMode: (m: Mode) => void;
  setActiveConnectionId: (id: string) => void;
  createChat: () => void;
  selectChat: (id: string) => void;
  sendMessage: (content: string) => void;
  deleteChat: (id: string) => void;
  renameChat: (id: string, title: string) => void;
  loadConnections: () => Promise<void>;
};

const ChatContext = createContext<ChatContextType | null>(null);

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("achillies");
  const [isLoading, setIsLoading] = useState(false);
  const [activeConnectionId, setActiveConnectionId] = useState<string | null>(null);
  const [connections, setConnections] = useState<any[]>([]);

  useEffect(() => {
    if (isAuthenticated) {
      loadConnections();
      loadConversations();
    }
  }, [isAuthenticated]);

  const loadConnections = async () => {
    try {
      const conns = await apiClient.getConnections();
      setConnections(conns);
      if (conns.length > 0 && !activeConnectionId) {
        setActiveConnectionId(conns[0].id);
      }
    } catch (error) {
      console.error("Failed to load connections:", error);
    }
  };

  const loadConversations = async () => {
    try {
      const conversations = await apiClient.getConversations();
      setChats(
        conversations.map((conv: any) => ({
          id: conv.id,
          title: conv.title,
          messages: conv.messages || [],
          createdAt: new Date(conv.created_at),
          updatedAt: new Date(conv.updated_at),
        }))
      );
    } catch (error) {
      console.error("Failed to load conversations:", error);
    }
  };

  const activeChat = chats.find((c) => c.id === activeChatId) || null;

  const createChat = useCallback(() => {
    const newChat: Chat = {
      id: crypto.randomUUID(),
      title: "New conversation",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(newChat.id);
  }, []);

  const selectChat = useCallback((id: string) => {
    setActiveChatId(id);
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      let chatId = activeChatId;

      if (!chatId) {
        const newChat: Chat = {
          id: crypto.randomUUID(),
          title: content.slice(0, 40) + (content.length > 40 ? "..." : ""),
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        chatId = newChat.id;
        setChats((prev) => [newChat, ...prev]);
        setActiveChatId(chatId);
      }

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      const assistantMsgId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      const targetChatId = chatId;
      setChats((prev) =>
        prev.map((c) =>
          c.id === targetChatId
            ? {
                ...c,
                messages: [...c.messages, userMsg, assistantMsg],
                title:
                  c.messages.length === 0
                    ? content.slice(0, 40) + (content.length > 40 ? "..." : "")
                    : c.title,
                updatedAt: new Date(),
              }
            : c
        )
      );

      setIsLoading(true);

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/chat/message/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
          },
          body: JSON.stringify({
            conversation_id: targetChatId,
            message: {
              id: userMsg.id,
              role: "user",
              content,
              timestamp: userMsg.timestamp.toISOString(),
            },
            connection_id: activeConnectionId || "",
            mode,
            execute_sql: false,
            stream: true,
          }),
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let textBuffer = "";
        let fullContent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          textBuffer += decoder.decode(value, { stream: true });

          let newlineIndex: number;
          while ((newlineIndex = textBuffer.indexOf("\n")) !== -1) {
            let line = textBuffer.slice(0, newlineIndex);
            textBuffer = textBuffer.slice(newlineIndex + 1);

            if (line.endsWith("\r")) line = line.slice(0, -1);
            if (line.startsWith(":") || line.trim() === "") continue;
            if (!line.startsWith("data: ")) continue;

            const jsonStr = line.slice(6).trim();
            if (jsonStr === "[DONE]") break;

            try {
              const parsed = JSON.parse(jsonStr);

              if (parsed.type === "content" || parsed.type === "token") {
                fullContent += parsed.content || parsed.token || "";
              } else if (parsed.type === "done") {
                // done
              } else if (parsed.choices?.[0]?.delta?.content) {
                fullContent += parsed.choices[0].delta.content;
              } else if (typeof parsed.content === "string") {
                fullContent += parsed.content;
              }

              setChats((prev) =>
                prev.map((c) =>
                  c.id === targetChatId
                    ? {
                        ...c,
                        messages: c.messages.map((m) =>
                          m.id === assistantMsgId ? { ...m, content: fullContent } : m
                        ),
                      }
                    : c
                )
              );
            } catch {
              textBuffer = line + "\n" + textBuffer;
              break;
            }
          }
        }

        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, isStreaming: false, content: fullContent || "I couldn't generate a response." }
                      : m
                  ),
                }
              : c
          )
        );
      } catch (error) {
        console.error("Streaming error:", error);
        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantMsgId
                      ? {
                          ...m,
                          isStreaming: false,
                          content: "Sorry, I couldn't connect to the server. Please check your backend is running.",
                        }
                      : m
                  ),
                }
              : c
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [activeChatId, mode, activeConnectionId]
  );

  const deleteChat = useCallback(
    (id: string) => {
      setChats((prev) => prev.filter((c) => c.id !== id));
      if (activeChatId === id) setActiveChatId(null);
    },
    [activeChatId]
  );

  const renameChat = useCallback((id: string, title: string) => {
    setChats((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
  }, []);

  return (
    <ChatContext.Provider
      value={{
        chats,
        activeChat,
        mode,
        isLoading,
        activeConnectionId,
        connections,
        setMode,
        setActiveConnectionId,
        createChat,
        selectChat,
        sendMessage,
        deleteChat,
        renameChat,
        loadConnections,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
