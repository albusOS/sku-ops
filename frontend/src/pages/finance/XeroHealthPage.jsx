import { RefreshCw, CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ReportPanel, ReportSectionHead } from "@/components/ReportPanel";
import { useXeroHealth, useTriggerXeroSync } from "@/hooks/useXeroHealth";
import { formatDate, formatMoney } from "@/lib/utils";

function DocTable({ rows, columns }) {
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/80 hover:bg-muted/80">
            {columns.map((col) => (
              <TableHead
                key={col.key}
                className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide"
              >
                {col.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={row.id ?? i} className="hover:bg-muted/60 transition-colors">
              {columns.map((col) => (
                <TableCell key={col.key} className="px-4 py-2.5 text-foreground">
                  {col.render ? col.render(row) : (row[col.key] ?? "—")}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

const FAILED_COLS = [
  { key: "doc_type", label: "Type" },
  { key: "doc_number", label: "Document" },
  { key: "name", label: "Name" },
  { key: "total", label: "Total", render: (r) => formatMoney(r.total) },
  { key: "created_at", label: "Created", render: (r) => formatDate(r.created_at) },
];

const MISMATCH_COLS = [
  { key: "doc_type", label: "Type" },
  { key: "doc_number", label: "Document" },
  { key: "name", label: "Name" },
  { key: "total", label: "Local Total", render: (r) => formatMoney(r.total) },
  {
    key: "xero_id",
    label: "Xero ID",
    render: (r) => (
      <span className="font-mono text-xs text-muted-foreground">{r.xero_id ?? "—"}</span>
    ),
  },
];

function normalizeFailedRows(data) {
  const rows = [];
  for (const inv of data?.failed_invoices ?? []) {
    rows.push({
      id: inv.id,
      doc_type: "Invoice",
      doc_number: inv.invoice_number,
      name: inv.billing_entity,
      total: inv.total,
      created_at: inv.created_at,
    });
  }
  for (const cn of data?.failed_credits ?? []) {
    rows.push({
      id: cn.id,
      doc_type: "Credit Note",
      doc_number: cn.credit_note_number,
      name: cn.billing_entity,
      total: cn.total,
      created_at: cn.created_at,
    });
  }
  for (const po of data?.failed_po_bills ?? []) {
    rows.push({
      id: po.id,
      doc_type: "Vendor Bill",
      doc_number: po.vendor_name,
      name: po.vendor_name,
      total: po.total,
      created_at: po.created_at,
    });
  }
  return rows;
}

function normalizeMismatchRows(data) {
  const rows = [];
  for (const inv of data?.mismatch_invoices ?? []) {
    rows.push({
      id: inv.id,
      doc_type: "Invoice",
      doc_number: inv.invoice_number,
      name: inv.billing_entity,
      total: inv.total,
      xero_id: inv.xero_invoice_id,
    });
  }
  for (const cn of data?.mismatch_credits ?? []) {
    rows.push({
      id: cn.id,
      doc_type: "Credit Note",
      doc_number: cn.credit_note_number,
      name: cn.billing_entity,
      total: cn.total,
      xero_id: cn.xero_credit_note_id,
    });
  }
  return rows;
}

export default function XeroHealthPage() {
  const { data, isLoading, error } = useXeroHealth();
  const { triggerSync, syncing, isPending } = useTriggerXeroSync();
  const isBusy = syncing || isPending;

  if (isLoading) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center text-muted-foreground text-sm">
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center text-destructive text-sm">
        Failed to load Xero status
      </div>
    );
  }

  const totals = data?.totals ?? {};
  const failedRows = normalizeFailedRows(data);
  const mismatchRows = normalizeMismatchRows(data);
  const pendingCount = totals.unsynced ?? 0;
  const hasProblems = failedRows.length > 0 || mismatchRows.length > 0;

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Xero Status</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Sales invoices, credit notes, and vendor bills that failed to sync or have mismatches
            with Xero.
          </p>
        </div>
        <Button onClick={() => triggerSync()} disabled={isBusy} className="gap-2" variant="outline">
          <RefreshCw className={`w-4 h-4 ${isBusy ? "animate-spin" : ""}`} />
          {isBusy ? "Syncing…" : "Sync Now"}
        </Button>
      </div>

      {!hasProblems && (
        <div className="flex items-center gap-2 text-success bg-success/10 border border-success/30 rounded-lg px-4 py-3 text-sm font-medium">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          All invoices, credit notes, and vendor bills are synced with Xero — no issues found.
        </div>
      )}

      <div className={`grid gap-4 ${pendingCount > 0 ? "grid-cols-3" : "grid-cols-2"}`}>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-2">
            <XCircle
              className={`w-4 h-4 ${failedRows.length > 0 ? "text-destructive" : "text-muted-foreground"}`}
            />
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Failed
            </p>
          </div>
          <p
            className={`text-3xl font-bold mt-1 ${failedRows.length > 0 ? "text-destructive" : "text-muted-foreground"}`}
          >
            {failedRows.length}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Could not push to Xero</p>
        </div>

        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle
              className={`w-4 h-4 ${mismatchRows.length > 0 ? "text-accent" : "text-muted-foreground"}`}
            />
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Mismatches
            </p>
          </div>
          <p
            className={`text-3xl font-bold mt-1 ${mismatchRows.length > 0 ? "text-accent" : "text-muted-foreground"}`}
          >
            {mismatchRows.length}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Data differs from Xero</p>
        </div>

        {pendingCount > 0 && (
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                Pending
              </p>
            </div>
            <p className="text-3xl font-bold mt-1 text-muted-foreground">{pendingCount}</p>
            <p className="text-xs text-muted-foreground mt-0.5">Waiting for next sync</p>
          </div>
        )}
      </div>

      {failedRows.length > 0 && (
        <ReportPanel>
          <ReportSectionHead
            title="Failed"
            action={
              <div className="flex items-center gap-2 shrink-0">
                <XCircle className="w-4 h-4 text-destructive" />
                <span className="text-xs font-medium px-1.5 py-0.5 rounded-full bg-destructive/15 text-destructive">
                  {failedRows.length}
                </span>
              </div>
            }
          />
          <p className="text-xs text-muted-foreground px-1 pb-3">
            These items could not be pushed to Xero. Run a sync to retry, or check Xero settings if
            failures persist.
          </p>
          <DocTable rows={failedRows} columns={FAILED_COLS} />
        </ReportPanel>
      )}

      {mismatchRows.length > 0 && (
        <ReportPanel>
          <ReportSectionHead
            title="Mismatches"
            action={
              <div className="flex items-center gap-2 shrink-0">
                <AlertTriangle className="w-4 h-4 text-accent" />
                <span className="text-xs font-medium px-1.5 py-0.5 rounded-full bg-warning/15 text-accent">
                  {mismatchRows.length}
                </span>
              </div>
            }
          />
          <p className="text-xs text-muted-foreground px-1 pb-3">
            The local total or line items differ from what Xero has. This usually means the record
            was edited locally after it was synced.
          </p>
          <DocTable rows={mismatchRows} columns={MISMATCH_COLS} />
        </ReportPanel>
      )}
    </div>
  );
}
