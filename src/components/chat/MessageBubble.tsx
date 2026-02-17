import { useState } from "react";
import type { Message } from "@/contexts/ChatContext";
import { cn } from "@/lib/utils";
import { Copy, ThumbsUp, ThumbsDown, RotateCcw, Check } from "lucide-react";

const linedTableClass =
  "border-collapse w-full border border-border [&_th]:border [&_th]:border-border [&_td]:border [&_td]:border-border [&_tr:first-child_th]:border-t-2 [&_tr:first-child_th]:border-t-border [&_tr:last-child_td]:border-b-2 [&_tr:last-child_td]:border-b-border";

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

  const dataPreview = message.dataPreview ?? null;
  const showDataPreview = dataPreview && dataPreview.columns && dataPreview.columns.length > 0;

  const results = message.results
    ? {
        columns: message.results.columns ?? [],
        rows: message.results.rows ?? [],
        totalRows: (message.results as any).total_rows ?? message.results.totalRows ?? 0,
        executionTimeMs: (message.results as any).execution_time_ms ?? message.results.executionTimeMs ?? 0,
      }
    : null;

  return (
    <div className="flex flex-col gap-3 max-w-[85%]">
      <div className="text-[15px] text-foreground whitespace-pre-wrap leading-relaxed">
        {message.content}
        {message.isStreaming && !message.content && (
          <span className="inline-block text-xl animate-pulse">✸</span>
        )}
        {message.isStreaming && message.content && (
          <span className="inline-block w-1.5 h-4 bg-foreground/70 ml-0.5 animate-pulse align-text-bottom" />
        )}
      </div>

      {/* Data preview: only when backend included data_preview (e.g. file upload) */}
      {showDataPreview && (
        <div className="rounded-lg border border-border bg-muted/30 overflow-hidden">
          <p className="text-xs font-medium text-muted-foreground px-3 py-2 border-b border-border">
            {dataPreview.label ?? "Data preview"}
          </p>
          <div className="overflow-x-auto p-2">
            <table className={linedTableClass}>
              <thead>
                <tr>
                  {dataPreview.columns.map((col, cidx) => (
                    <th key={cidx} className="h-8 px-2 text-xs text-left font-medium text-muted-foreground border-border">
                      {col.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(dataPreview.rows ?? []).map((row, ridx) => (
                  <tr key={ridx}>
                    {dataPreview.columns.map((_, cidx) => (
                      <td key={cidx} className="py-1.5 px-2 text-xs font-mono border-border">
                        {String((row as unknown[])[cidx] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {message.schemaUsed && message.schemaUsed.length > 0 && (
        <div className="rounded-lg border border-border bg-muted/30 overflow-hidden">
          <p className="text-xs font-medium text-muted-foreground px-3 py-2 border-b border-border">
            Schema used for this answer
          </p>
          <div className="p-2 space-y-3">
            {message.schemaUsed.map((tbl, idx) => (
              <div key={idx} className="overflow-hidden">
                <p className="text-xs font-medium px-2 py-1.5 bg-muted/50 text-foreground mb-0">
                  {tbl.schema_name ? `${tbl.schema_name}.${tbl.table_name}` : tbl.table_name}
                </p>
                <table className={cn("mt-0", linedTableClass)}>
                  <thead>
                    <tr>
                      <th className="h-8 px-2 text-xs text-left font-medium text-muted-foreground">Column</th>
                      <th className="h-8 px-2 text-xs text-left font-medium text-muted-foreground">Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(tbl.columns || []).map((col, cidx) => (
                      <tr key={cidx}>
                        <td className="py-1.5 px-2 text-xs font-mono border-border">{col.name}</td>
                        <td className="py-1.5 px-2 text-xs text-muted-foreground border-border">{col.type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </div>
      )}

      {message.explanationAfterSchema && (
        <p className="text-sm text-foreground leading-relaxed">
          {message.explanationAfterSchema}
        </p>
      )}

      {message.sql?.query && (
        <div className="rounded-lg border border-border bg-muted/30 overflow-hidden">
          <p className="text-xs font-medium text-muted-foreground px-3 py-2 border-b border-border">
            SQL
          </p>
          <div className="p-3 space-y-3">
            {message.sql.explanation && (
              <p className="text-sm text-foreground leading-relaxed">
                {message.sql.explanation}
              </p>
            )}
            <pre className="text-xs font-mono text-foreground overflow-x-auto whitespace-pre-wrap">
              <code>{message.sql.query}</code>
            </pre>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {message.explanationBeforeResult ?? "The query above returns the following result."}
            </p>
          </div>
        </div>
      )}

      {results && results.columns.length > 0 && (
        <div className="rounded-lg border border-border bg-muted/30 overflow-hidden">
          <p className="text-xs font-medium text-muted-foreground px-3 py-2 border-b border-border">
            Result ({results.totalRows} row{results.totalRows !== 1 ? "s" : ""}, {results.executionTimeMs}ms)
          </p>
          <div className="overflow-x-auto p-2">
            <table className={linedTableClass}>
              <thead>
                <tr>
                  {results.columns.map((col, cidx) => (
                    <th key={cidx} className="h-8 px-2 text-xs text-left font-medium text-muted-foreground border-border">
                      {col.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(results.rows ?? []).map((row, ridx) => (
                  <tr key={ridx}>
                    {results.columns.map((_, cidx) => (
                      <td key={cidx} className="py-1.5 px-2 text-xs font-mono border-border">
                        {String(row[cidx] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

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
