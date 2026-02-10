import { useState } from "react";
import type { Message } from "@/contexts/ChatContext";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import {
  Database,
  Copy,
  Play,
  Pencil,
  ChevronDown,
  ChevronRight,
  Check,
  Download,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function ToolEventChip({ event }: { event: { icon: string; label: string; durationMs: number; details?: string } }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(!open)}
      className="flex items-center gap-1.5 rounded-full bg-surface px-2.5 py-1 text-xs text-muted-foreground hover:bg-accent transition-colors"
    >
      <span>{event.icon}</span>
      <span>{event.label}</span>
      <span className="text-muted-foreground/60">{(event.durationMs / 1000).toFixed(1)}s</span>
      {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
    </button>
  );
}

function SQLPanel({ sql }: { sql: { query: string; dialect: string } }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql.query);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3 rounded-xl overflow-hidden border border-border">
      <div className="flex items-center justify-between bg-foreground px-3 py-1.5">
        <span className="text-[11px] font-medium text-primary font-mono">{sql.dialect}</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] text-background/60 hover:text-background hover:bg-background/10" onClick={handleCopy}>
            {copied ? <Check className="h-3 w-3 mr-1" /> : <Copy className="h-3 w-3 mr-1" />}
            {copied ? "Copied" : "Copy"}
          </Button>
          <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] text-background/60 hover:text-background hover:bg-background/10">
            <Pencil className="h-3 w-3 mr-1" />
            Edit
          </Button>
          <Button size="sm" className="h-6 px-2.5 text-[11px] bg-success hover:bg-success/90 text-success-foreground">
            <Play className="h-3 w-3 mr-1" />
            Run Query
          </Button>
        </div>
      </div>
      <pre className="bg-foreground/95 px-4 py-3 overflow-x-auto">
        <code className="text-code font-mono text-background/80 whitespace-pre">{sql.query}</code>
      </pre>
    </div>
  );
}

function ResultViewer({ results }: { results: NonNullable<Message["results"]> }) {
  const chartData = results.rows.map((row) => {
    const obj: Record<string, any> = {};
    results.columns.forEach((col, i) => {
      obj[col.name] = row[i];
    });
    return obj;
  });

  const numericCols = results.columns.filter((c) => c.type === "numeric" || c.type === "integer");
  const labelCol = results.columns.find((c) => c.type === "text" || c.type === "date");

  return (
    <div className="mt-3 rounded-xl border border-border overflow-hidden">
      <Tabs defaultValue="table" className="w-full">
        <div className="flex items-center justify-between border-b border-border px-3 py-1">
          <TabsList className="h-7 bg-transparent p-0 gap-0">
            <TabsTrigger value="table" className="h-7 text-xs rounded-md data-[state=active]:bg-accent px-2.5">Table</TabsTrigger>
            <TabsTrigger value="chart" className="h-7 text-xs rounded-md data-[state=active]:bg-accent px-2.5">Chart</TabsTrigger>
            <TabsTrigger value="json" className="h-7 text-xs rounded-md data-[state=active]:bg-accent px-2.5">JSON</TabsTrigger>
          </TabsList>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span>{results.totalRows} rows · {results.executionTimeMs}ms</span>
            <Button variant="ghost" size="sm" className="h-6 px-1.5">
              <Download className="h-3 w-3" />
            </Button>
          </div>
        </div>

        <TabsContent value="table" className="m-0">
          <div className="max-h-[400px] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface">
                <tr>
                  {results.columns.map((col) => (
                    <th key={col.name} className="px-3 py-2 text-left text-xs font-medium text-muted-foreground border-b border-border">
                      {col.name}
                      <span className="ml-1.5 text-[10px] font-normal text-muted-foreground/60">{col.type}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.rows.map((row, i) => (
                  <tr key={i} className={cn("border-b border-border", i % 2 === 1 && "bg-surface/50")}>
                    {row.map((cell, j) => (
                      <td key={j} className="px-3 py-1.5 text-sm font-mono">
                        {typeof cell === "number" ? cell.toLocaleString() : String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="chart" className="m-0 p-4">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey={labelCol?.name || results.columns[0].name}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              {numericCols.slice(0, 2).map((col, i) => (
                <Bar
                  key={col.name}
                  dataKey={col.name}
                  fill={i === 0 ? "hsl(var(--primary))" : "hsl(var(--success))"}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </TabsContent>

        <TabsContent value="json" className="m-0">
          <pre className="max-h-[400px] overflow-auto p-4 text-code font-mono text-muted-foreground">
            {JSON.stringify(
              results.rows.map((row) => {
                const obj: Record<string, any> = {};
                results.columns.forEach((col, i) => (obj[col.name] = row[i]));
                return obj;
              }),
              null,
              2
            )}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function MessageBubble({ message }: { message: Message }) {
  const { user } = useAuth();

  if (message.role === "user") {
    return (
      <div className="flex gap-3 justify-end group">
        <div className="max-w-[85%] rounded-2xl bg-surface px-4 py-2.5">
          <p className="text-message text-foreground whitespace-pre-wrap">{message.content}</p>
        </div>
        <Avatar className="h-7 w-7 shrink-0 mt-0.5">
          <AvatarFallback className="text-[11px] bg-primary text-primary-foreground">
            {user?.name?.[0]?.toUpperCase() || "U"}
          </AvatarFallback>
        </Avatar>
      </div>
    );
  }

  if (message.role === "system") {
    return (
      <div className="rounded-xl border border-warning/30 bg-warning/5 px-4 py-2.5 text-sm text-warning">
        {message.content}
      </div>
    );
  }

  // Assistant
  return (
    <div className="flex gap-3">
      <Avatar className="h-7 w-7 shrink-0 mt-0.5">
        <AvatarFallback className="text-[11px] bg-foreground text-background">
          <Database className="h-3.5 w-3.5" />
        </AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0 space-y-2">
        {/* Tool events */}
        {message.toolEvents && message.toolEvents.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.toolEvents.map((ev) => (
              <ToolEventChip key={ev.id} event={ev} />
            ))}
          </div>
        )}

        {/* Text */}
        <p className="text-message text-foreground whitespace-pre-wrap">{message.content}</p>

        {/* SQL */}
        {message.sql && <SQLPanel sql={message.sql} />}

        {/* Results */}
        {message.results && <ResultViewer results={message.results} />}

        {/* Action buttons */}
        {message.results && (
          <div className="flex gap-2 pt-1">
            <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground">
              Refine filters
            </Button>
            <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground">
              Add grouping
            </Button>
            <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground">
              Explain plan
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
