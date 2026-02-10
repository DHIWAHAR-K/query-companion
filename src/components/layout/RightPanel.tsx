import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Search,
  Database,
  Table2,
  Columns3,
  ChevronRight,
  ChevronDown,
  Check,
  X as XIcon,
  Clock,
  Lightbulb,
  PanelRightClose,
} from "lucide-react";

// Mock schema tree
const mockSchema = [
  {
    name: "public",
    tables: [
      {
        name: "orders",
        rowCount: 45231,
        columns: [
          { name: "id", type: "uuid" },
          { name: "customer_id", type: "uuid" },
          { name: "total_amount", type: "numeric" },
          { name: "status", type: "text" },
          { name: "created_at", type: "timestamp" },
          { name: "region_id", type: "integer" },
        ],
      },
      {
        name: "customers",
        rowCount: 12453,
        columns: [
          { name: "id", type: "uuid" },
          { name: "name", type: "text" },
          { name: "email", type: "text" },
          { name: "created_at", type: "timestamp" },
        ],
      },
      {
        name: "regions",
        rowCount: 12,
        columns: [
          { name: "id", type: "integer" },
          { name: "region_name", type: "text" },
          { name: "country_code", type: "text" },
        ],
      },
      {
        name: "products",
        rowCount: 847,
        columns: [
          { name: "id", type: "uuid" },
          { name: "name", type: "text" },
          { name: "price", type: "numeric" },
          { name: "category", type: "text" },
        ],
      },
      {
        name: "user_events",
        rowCount: 1234567,
        columns: [
          { name: "id", type: "bigint" },
          { name: "user_id", type: "uuid" },
          { name: "event_type", type: "text" },
          { name: "event_timestamp", type: "timestamp" },
        ],
      },
    ],
  },
];

const mockHistory = [
  { sql: "SELECT region_name, SUM(total_amount) FROM orders...", time: 142, success: true, when: "2 min ago" },
  { sql: "SELECT COUNT(DISTINCT user_id) FROM user_events...", time: 89, success: true, when: "15 min ago" },
  { sql: "SELECT * FROM orders WHERE status = 'failed'...", time: 234, success: false, when: "1 hour ago" },
];

const mockSuggestions = [
  { title: "Weekly sales by region", description: "Aggregates orders by region with weekly grouping" },
  { title: "Top customers by revenue", description: "Finds highest-spending customers in the last 90 days" },
  { title: "Product category breakdown", description: "Revenue distribution across product categories" },
  { title: "Daily active users trend", description: "User engagement over the last 30 days" },
];

const typeBadgeColor: Record<string, string> = {
  uuid: "bg-purple-100 text-purple-700",
  text: "bg-blue-100 text-blue-700",
  numeric: "bg-green-100 text-green-700",
  integer: "bg-green-100 text-green-700",
  bigint: "bg-green-100 text-green-700",
  timestamp: "bg-amber-100 text-amber-700",
  date: "bg-amber-100 text-amber-700",
};

function SchemaExplorer() {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ public: true });

  const toggle = (key: string) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          placeholder="Search tables..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 pl-8 text-xs"
        />
      </div>
      <div className="space-y-0.5 text-sm">
        {mockSchema.map((schema) => (
          <div key={schema.name}>
            <button
              onClick={() => toggle(schema.name)}
              className="flex items-center gap-1.5 w-full px-1 py-1 rounded hover:bg-accent text-xs font-medium"
            >
              {expanded[schema.name] ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              <Database className="h-3 w-3 text-muted-foreground" />
              {schema.name}
            </button>
            {expanded[schema.name] &&
              schema.tables
                .filter((t) => !search || t.name.toLowerCase().includes(search.toLowerCase()))
                .map((table) => (
                  <div key={table.name} className="ml-3">
                    <button
                      onClick={() => toggle(`${schema.name}.${table.name}`)}
                      className="flex items-center gap-1.5 w-full px-1 py-1 rounded hover:bg-accent text-xs"
                    >
                      {expanded[`${schema.name}.${table.name}`] ? (
                        <ChevronDown className="h-3 w-3" />
                      ) : (
                        <ChevronRight className="h-3 w-3" />
                      )}
                      <Table2 className="h-3 w-3 text-muted-foreground" />
                      <span className="font-medium">{table.name}</span>
                      <span className="text-[10px] text-muted-foreground ml-auto">{table.rowCount.toLocaleString()}</span>
                    </button>
                    {expanded[`${schema.name}.${table.name}`] && (
                      <div className="ml-5 space-y-0.5 py-0.5">
                        {table.columns.map((col) => (
                          <div key={col.name} className="flex items-center gap-1.5 px-1 py-0.5 text-xs text-muted-foreground">
                            <Columns3 className="h-3 w-3" />
                            <span>{col.name}</span>
                            <span className={cn("ml-auto rounded px-1 py-0 text-[10px] font-medium", typeBadgeColor[col.type] || "bg-muted text-muted-foreground")}>
                              {col.type}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
          </div>
        ))}
      </div>
    </div>
  );
}

interface RightPanelProps {
  onClose: () => void;
}

export default function RightPanel({ onClose }: RightPanelProps) {
  return (
    <div className="flex h-full w-[380px] flex-col border-l border-border bg-background">
      <div className="flex items-center justify-between px-3 h-[52px] border-b border-border shrink-0">
        <span className="text-sm font-medium text-foreground">Context</span>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <PanelRightClose className="h-4 w-4" />
        </Button>
      </div>

      <Tabs defaultValue="schema" className="flex-1 flex flex-col min-h-0">
        <TabsList className="mx-3 mt-2 h-8 bg-surface p-0.5 w-auto">
          <TabsTrigger value="schema" className="h-7 text-xs px-2.5">Schema</TabsTrigger>
          <TabsTrigger value="history" className="h-7 text-xs px-2.5">History</TabsTrigger>
          <TabsTrigger value="suggestions" className="h-7 text-xs px-2.5">Suggestions</TabsTrigger>
        </TabsList>

        <TabsContent value="schema" className="flex-1 overflow-y-auto p-3 m-0">
          <SchemaExplorer />
        </TabsContent>

        <TabsContent value="history" className="flex-1 overflow-y-auto p-3 m-0 space-y-2">
          {mockHistory.map((item, i) => (
            <div key={i} className="rounded-lg border border-border p-2.5 cursor-pointer hover:bg-accent transition-colors">
              <p className="text-xs font-mono text-foreground truncate">{item.sql}</p>
              <div className="flex items-center gap-2 mt-1.5 text-[11px] text-muted-foreground">
                {item.success ? (
                  <span className="flex items-center gap-0.5 text-success"><Check className="h-3 w-3" /> Success</span>
                ) : (
                  <span className="flex items-center gap-0.5 text-destructive"><XIcon className="h-3 w-3" /> Failed</span>
                )}
                <span>·</span>
                <span>{item.time}ms</span>
                <span>·</span>
                <span><Clock className="h-3 w-3 inline mr-0.5" />{item.when}</span>
              </div>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="suggestions" className="flex-1 overflow-y-auto p-3 m-0 space-y-2">
          {mockSuggestions.map((item, i) => (
            <div key={i} className="rounded-lg border border-border p-3 cursor-pointer hover:bg-accent transition-colors">
              <div className="flex items-start gap-2">
                <Lightbulb className="h-4 w-4 text-warning shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-foreground">{item.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                </div>
              </div>
            </div>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}
