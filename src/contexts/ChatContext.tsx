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

// Mock assistant responses
const mockResponses: { content: string; sql?: SQLBlock; toolEvents?: ToolEvent[]; results?: QueryResult }[] = [
  {
    content: "I found the data you're looking for. Here's a query to get the total sales by region for the last quarter:",
    toolEvents: [
      { id: "1", label: "Searched schema: sales_data", icon: "🔍", durationMs: 1200 },
      { id: "2", label: "Analyzed table structure", icon: "📊", durationMs: 800 },
    ],
    sql: {
      query: `SELECT \n  r.region_name,\n  SUM(o.total_amount) AS total_sales,\n  COUNT(o.id) AS order_count,\n  AVG(o.total_amount) AS avg_order_value\nFROM orders o\nJOIN regions r ON o.region_id = r.id\nWHERE o.created_at >= NOW() - INTERVAL '3 months'\nGROUP BY r.region_name\nORDER BY total_sales DESC;`,
      dialect: "PostgreSQL",
    },
    results: {
      columns: [
        { name: "region_name", type: "text" },
        { name: "total_sales", type: "numeric" },
        { name: "order_count", type: "integer" },
        { name: "avg_order_value", type: "numeric" },
      ],
      rows: [
        ["North America", 1245890.5, 3421, 364.19],
        ["Europe", 987654.32, 2876, 343.41],
        ["Asia Pacific", 756123.45, 2134, 354.33],
        ["Latin America", 432567.89, 1245, 347.44],
        ["Middle East", 234567.12, 876, 267.77],
      ],
      totalRows: 5,
      executionTimeMs: 142,
    },
  },
  {
    content: "Here's the user activity breakdown you requested. The query analyzes daily active users over the past week:",
    toolEvents: [
      { id: "1", label: "Fetched schema: analytics", icon: "🔍", durationMs: 950 },
    ],
    sql: {
      query: `SELECT \n  DATE(event_timestamp) AS activity_date,\n  COUNT(DISTINCT user_id) AS daily_active_users,\n  COUNT(*) AS total_events\nFROM user_events\nWHERE event_timestamp >= CURRENT_DATE - INTERVAL '7 days'\nGROUP BY DATE(event_timestamp)\nORDER BY activity_date;`,
      dialect: "PostgreSQL",
    },
    results: {
      columns: [
        { name: "activity_date", type: "date" },
        { name: "daily_active_users", type: "integer" },
        { name: "total_events", type: "integer" },
      ],
      rows: [
        ["2026-02-03", 1245, 15678],
        ["2026-02-04", 1312, 16432],
        ["2026-02-05", 1189, 14567],
        ["2026-02-06", 1456, 18234],
        ["2026-02-07", 1523, 19012],
        ["2026-02-08", 987, 12345],
        ["2026-02-09", 1034, 13456],
      ],
      totalRows: 7,
      executionTimeMs: 89,
    },
  },
  {
    content: "I can help with that! Let me look into the database structure for you.",
    toolEvents: [
      { id: "1", label: "Exploring database schema", icon: "🗄️", durationMs: 600 },
    ],
  },
];

let responseIndex = 0;

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [chats, setChats] = useState<Chat[]>([
    {
      id: "demo-1",
      title: "Sales by region analysis",
      messages: [],
      createdAt: new Date(Date.now() - 3600000),
      updatedAt: new Date(Date.now() - 3600000),
    },
    {
      id: "demo-2",
      title: "User activity metrics",
      messages: [],
      createdAt: new Date(Date.now() - 86400000),
      updatedAt: new Date(Date.now() - 86400000),
    },
    {
      id: "demo-3",
      title: "Revenue forecasting query",
      messages: [],
      createdAt: new Date(Date.now() - 86400000 * 3),
      updatedAt: new Date(Date.now() - 86400000 * 3),
    },
  ]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("achillies");

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

  const sendMessage = useCallback((content: string) => {
    setChats((prev) => {
      let chatId = activeChatId;
      let updated = [...prev];

      if (!chatId) {
        const newChat: Chat = {
          id: crypto.randomUUID(),
          title: content.slice(0, 40) + (content.length > 40 ? "..." : ""),
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        updated = [newChat, ...updated];
        chatId = newChat.id;
        setTimeout(() => setActiveChatId(chatId), 0);
      }

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      const mockResp = mockResponses[responseIndex % mockResponses.length];
      responseIndex++;

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: mockResp.content,
        timestamp: new Date(),
        toolEvents: mockResp.toolEvents,
        sql: mockResp.sql,
        results: mockResp.results,
      };

      return updated.map((c) =>
        c.id === chatId
          ? {
              ...c,
              messages: [...c.messages, userMsg, assistantMsg],
              title: c.messages.length === 0 ? content.slice(0, 40) + (content.length > 40 ? "..." : "") : c.title,
              updatedAt: new Date(),
            }
          : c
      );
    });
  }, [activeChatId]);

  const deleteChat = useCallback((id: string) => {
    setChats((prev) => prev.filter((c) => c.id !== id));
    if (activeChatId === id) setActiveChatId(null);
  }, [activeChatId]);

  const renameChat = useCallback((id: string, title: string) => {
    setChats((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
  }, []);

  return (
    <ChatContext.Provider
      value={{ chats, activeChat, mode, setMode, createChat, selectChat, sendMessage, deleteChat, renameChat }}
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
