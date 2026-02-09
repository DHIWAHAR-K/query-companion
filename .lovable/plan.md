

# Queryus — AI-Powered SQL Chat Assistant

A ChatGPT-style interface for natural language to SQL, with three-panel layout, mock data, and authentication.

---

## Phase 1: Authentication

- **Login / Signup page** with email & password using Supabase (Lovable Cloud)
- User profiles table (name, avatar)
- User roles table for future admin capabilities
- Protected routes — redirect unauthenticated users to login

---

## Phase 2: Core Layout Shell

- **Three-column adaptive layout** mimicking ChatGPT:
  - **Left sidebar** (240px, collapsible): logo/wordmark, "New Chat" button, connection selector dropdown, chat history grouped by Today/Yesterday/Last 7 days/Last 30 days, user avatar + settings at bottom, mode indicator badge
  - **Center chat pane** (flex-1): header with chat title + mode switcher pills + share button, message area (768px max-width centered), fixed input area at bottom
  - **Right panel** (400px, collapsible): Schema Explorer, Query History, Suggestions tabs
- Responsive behavior: right panel hidden on smaller screens, sidebar collapsible to mini mode with icons

---

## Phase 3: Chat Interface

- **User message bubbles**: light gray background, right-aligned avatar, markdown rendering, image attachment thumbnails, hover-to-edit
- **Assistant message bubbles**: no background, left-aligned Queryus avatar, with stacked sections:
  - Thinking/tool-use accordion chips with timestamps
  - Markdown-rendered text explanation
  - SQL code panel (dark theme, syntax highlighted, with dialect badge, copy, edit, and "Run Query" buttons)
  - Result viewer with Table / Chart / Raw JSON tabs
  - Action buttons: "Refine filters", "Add grouping", "Explain plan"
- **System messages**: yellow/red banners for errors/warnings with collapsible details
- **Input area**: attachment button, auto-expanding textarea, send button, disclaimer micro-text
- Attachment preview area with thumbnail chips above input

---

## Phase 4: Mode Switcher (Valtryek / Achillies / Spryzen)

- Three pill-style buttons in the chat header representing AI model tiers (fast / balanced / deep)
- Confirmation modal when switching mid-conversation
- Mode indicator badge in sidebar bottom section
- Each mode visually distinguished (subtle color/icon differences)

---

## Phase 5: Result Viewer

- **Table view**: sticky header, zebra-striped rows, scrollable (max 400px), row count footer, pagination, CSV download
- **Chart view**: auto-suggested chart type based on data shape (bar/line/pie), chart type selector dropdown, powered by Recharts
- **Raw JSON view**: collapsible tree with copy button

---

## Phase 6: Right Panel — Schema Explorer, History & Suggestions

- **Schema Explorer**: search box, tree view (database → schema → table with row count → columns with type badges), click-to-insert table name, right-click for "Sample rows" or "Show DDL"
- **Query History**: recent queries list with SQL snippet, execution time, success/fail status, timestamp, click to load
- **Suggestions**: predefined query template cards with title + description, click to paste

---

## Phase 7: Chat History & Management

- Sidebar chat list with truncated first message, timestamp, 3-dot menu (rename, delete)
- Active chat highlighted
- Grouped by time period (Today, Yesterday, Last 7 days, Last 30 days)
- Editable chat titles (click to rename in header)

---

## Design System

- **Colors**: White background, #F7F7F8 surfaces, #2563EB primary blue, #10B981 success green, #F59E0B warning amber, #EF4444 error red
- **Typography**: Inter/system-ui for UI, Fira Code/monospace for code, 15px message text, 13px code
- **Spacing**: 4px base scale
- **ChatGPT-inspired aesthetics**: clean, minimal, generous whitespace, subtle shadows

---

## Technical Notes

- All data will be **mocked** for now — sample SQL queries, fake schema trees, pre-built result sets
- Backend integration (real DB connections, AI SQL generation, query execution) planned for a future phase
- Authentication via Lovable Cloud (Supabase)

