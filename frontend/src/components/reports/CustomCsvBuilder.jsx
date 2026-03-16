import { useState, useMemo, useCallback } from "react";
import { Download, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ReportPanel, ReportSectionHead } from "@/components/ReportPanel";
import { valueFormatter } from "@/lib/chartConfig";
import { format } from "date-fns";

/**
 * Build and export custom CSV tables from report data.
 * User selects data source, picks columns, then exports.
 *
 * @param {Object} props
 * @param {Array<{ id: string, label: string, getRows: () => Array<object>, getDefaultColumns: () => Array<{ key: string, label: string }> }>} props.sources
 */
export function CustomCsvBuilder({ sources }) {
  const [sourceId, setSourceId] = useState(sources[0]?.id ?? "");
  const [selectedColumnKeys, setSelectedColumnKeys] = useState(null);

  const source = useMemo(
    () => sources.find((s) => s.id === sourceId) ?? sources[0],
    [sources, sourceId],
  );
  const rows = useMemo(() => (source?.getRows?.() ?? []) || [], [source]);
  const allColumns = useMemo(
    () => source?.getDefaultColumns?.() ?? inferColumns(rows),
    [source, rows],
  );

  const columns = useMemo(() => {
    const keys = selectedColumnKeys ?? allColumns.map((c) => c.key);
    return allColumns.filter((c) => keys.includes(c.key));
  }, [allColumns, selectedColumnKeys]);

  const handleExport = useCallback(() => {
    if (rows.length === 0) return;
    const header = columns.map((c) => `"${(c.label || c.key).replace(/"/g, '""')}"`).join(",");
    const dataRows = rows.map((row) =>
      columns
        .map((c) => {
          const val = row[c.key];
          const str = val == null ? "" : String(val);
          return `"${str.replace(/"/g, '""')}"`;
        })
        .join(","),
    );
    const csv = [header, ...dataRows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${sourceId}-${format(new Date(), "yyyy-MM-dd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [rows, columns, sourceId]);

  const toggleColumn = useCallback(
    (key) => {
      setSelectedColumnKeys((prev) => {
        const current = prev ?? allColumns.map((c) => c.key);
        if (current.includes(key)) {
          if (current.length <= 1) return current;
          return current.filter((k) => k !== key);
        }
        return [...current, key];
      });
    },
    [allColumns],
  );

  return (
    <Collapsible defaultOpen>
      <ReportPanel>
        <ReportSectionHead
          title="Build custom CSV"
          action={
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground">
                <ChevronDown className="w-4 h-4 data-[state=open]:rotate-180 transition-transform" />
                Expand
              </Button>
            </CollapsibleTrigger>
          }
        />
        <CollapsibleContent>
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs font-medium text-muted-foreground">Data source</label>
              <Select
                value={sourceId}
                onValueChange={(v) => {
                  setSourceId(v);
                  setSelectedColumnKeys(null);
                }}
              >
                <SelectTrigger className="w-[220px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {sources.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Include columns</p>
              <div className="flex flex-wrap gap-2">
                {allColumns.map((c) => {
                  const active = (selectedColumnKeys ?? allColumns.map((x) => x.key)).includes(
                    c.key,
                  );
                  return (
                    <label
                      key={c.key}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-border/60 cursor-pointer hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => toggleColumn(c.key)}
                        className="rounded"
                      />
                      <span className="text-xs">{c.label || c.key}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {rows.length > 0 && (
              <div className="rounded-lg border border-border overflow-hidden">
                <div className="max-h-[200px] overflow-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-muted/50 border-b border-border">
                        {columns.map((c) => (
                          <th
                            key={c.key}
                            className="px-3 py-2 text-left font-medium text-muted-foreground"
                          >
                            {c.label || c.key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.slice(0, 20).map((row, i) => (
                        <tr key={i} className="border-b border-border/50 last:border-0">
                          {columns.map((c) => {
                            const val = row[c.key];
                            const display =
                              typeof val === "number" &&
                              (c.key.includes("revenue") ||
                                c.key.includes("cost") ||
                                c.key.includes("profit") ||
                                c.key.includes("value"))
                                ? valueFormatter(val)
                                : val;
                            return (
                              <td key={c.key} className="px-3 py-2 tabular-nums">
                                {display ?? "\u2014"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {rows.length > 20 && (
                  <p className="text-[10px] text-muted-foreground px-3 py-1.5 bg-muted/30">
                    Showing first 20 of {rows.length} rows
                  </p>
                )}
              </div>
            )}

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleExport}
                disabled={rows.length === 0}
                className="gap-2"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </Button>
              <span className="text-xs text-muted-foreground">
                {rows.length} rows · {columns.length} columns
              </span>
            </div>
          </div>
        </CollapsibleContent>
      </ReportPanel>
    </Collapsible>
  );
}

function inferColumns(rows) {
  if (!rows.length) return [];
  const keys = Object.keys(rows[0]);
  return keys.map((k) => ({
    key: k,
    label: k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  }));
}
