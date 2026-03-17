import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ShoppingCart, ScanBarcode, Send, FileText, RotateCcw, HardHat } from "lucide-react";
import { format } from "date-fns";
import { Panel } from "@/components/Panel";
import { StatusBadge } from "@/components/StatusBadge";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { InvoiceDetailModal } from "@/components/InvoiceDetailModal";
import { PendingRequestsSection } from "@/components/operations/PendingRequestsSection";
import { ReturnDetailPanel } from "@/components/operations/ReturnDetailPanel";
import { CreateReturnModal } from "@/components/operations/CreateReturnModal";
import { useMaterialRequests, useProcessMaterialRequest } from "@/hooks/useMaterialRequests";
import { useInvoices, useSyncXero, useBulkSyncXero } from "@/hooks/useInvoices";
import { useReturns } from "@/hooks/useReturns";
import { useViewController } from "@/hooks/useViewController";
import { getErrorMessage } from "@/lib/api-client";
import { dateToISO, endOfDayISO } from "@/lib/utils";
import { DATE_PRESETS } from "@/lib/constants";

const INVOICE_COLUMNS = [
  {
    key: "invoice_number",
    label: "Invoice #",
    type: "text",
    render: (row) => <span className="font-mono text-xs font-medium">{row.invoice_number}</span>,
    exportValue: (row) => row.invoice_number,
  },
  {
    key: "billing_entity",
    label: "Entity",
    type: "enum",
    render: (row) => <span className="text-muted-foreground">{row.billing_entity || "—"}</span>,
  },
  {
    key: "total",
    label: "Total",
    type: "number",
    align: "right",
    render: (row) => (
      <span className="font-semibold tabular-nums">${(row.total ?? 0).toFixed(2)}</span>
    ),
    exportValue: (row) => (row.total ?? 0).toFixed(2),
  },
  {
    key: "status",
    label: "Status",
    type: "enum",
    filterValues: ["draft", "approved", "sent", "paid"],
    render: (row) => <StatusBadge status={row.status} />,
    exportValue: (row) => row.status,
  },
  {
    key: "invoice_date",
    label: "Date",
    type: "date",
    render: (row) => {
      const d = row.invoice_date || row.created_at;
      return (
        <span className="font-mono text-xs text-muted-foreground">
          {d ? format(new Date(d), "MMM d, yyyy") : "—"}
        </span>
      );
    },
    exportValue: (row) => row.invoice_date || row.created_at || "",
  },
  {
    key: "due_date",
    label: "Due",
    type: "date",
    render: (row) => {
      if (!row.due_date) return "—";
      const overdue = row.status !== "paid" && new Date(row.due_date) < new Date();
      return (
        <span
          className={`font-mono text-xs ${overdue ? "text-destructive font-semibold" : "text-muted-foreground"}`}
        >
          {format(new Date(row.due_date), "MMM d, yyyy")}
        </span>
      );
    },
    exportValue: (row) => row.due_date || "",
  },
  {
    key: "withdrawal_count",
    label: "Sales",
    type: "number",
    align: "right",
    render: (row) => (
      <span className="font-mono text-muted-foreground">{row.withdrawal_count ?? 0}</span>
    ),
  },
];

const RETURN_COLUMNS = [
  {
    key: "created_at",
    label: "Date",
    type: "date",
    render: (row) => (
      <span className="font-mono text-xs text-muted-foreground">
        {new Date(row.created_at).toLocaleDateString()}
      </span>
    ),
  },
  {
    key: "contractor_name",
    label: "Contractor",
    type: "text",
    render: (row) => (
      <div className="flex items-center gap-2">
        <HardHat className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        <span className="font-medium text-foreground">{row.contractor_name || "—"}</span>
      </div>
    ),
  },
  {
    key: "reason",
    label: "Reason",
    type: "enum",
    filterValues: ["wrong_item", "defective", "overorder", "job_cancelled", "other"],
    render: (row) => (
      <span className="text-xs capitalize text-muted-foreground">
        {(row.reason || "other").replace(/_/g, " ")}
      </span>
    ),
  },
  {
    key: "total",
    label: "Refund",
    type: "number",
    align: "right",
    render: (row) => (
      <span className="font-semibold tabular-nums text-destructive">
        -${(row.total || 0).toFixed(2)}
      </span>
    ),
  },
  {
    key: "credit_note_id",
    label: "Credit Note",
    type: "text",
    render: (row) =>
      row.credit_note_id ? (
        <StatusBadge status="approved" className="text-[10px]" />
      ) : (
        <span className="text-xs text-muted-foreground">—</span>
      ),
  },
];

export default function PointOfSale() {
  const defaultRange = DATE_PRESETS[1].getValue();
  const [dateRange, setDateRange] = useState(defaultRange);

  const dateParams = useMemo(
    () => ({
      start_date: dateToISO(dateRange.from),
      end_date: endOfDayISO(dateRange.to),
    }),
    [dateRange],
  );

  const {
    data: allRequests,
    isLoading: requestsLoading,
    isError: requestsError,
    error: requestsErr,
    refetch: refetchRequests,
  } = useMaterialRequests(undefined, { refetchInterval: 30000 });
  const processRequest = useProcessMaterialRequest();

  const requests = (allRequests || []).filter((r) => r.status === "pending");

  const { data: invoices = [] } = useInvoices(dateParams);
  const syncXero = useSyncXero();
  const bulkSyncXero = useBulkSyncXero();

  const { data: returns = [] } = useReturns(dateParams);

  const [detailInvoiceId, setDetailInvoiceId] = useState(null);
  const [detailReturnId, setDetailReturnId] = useState(null);
  const [createReturnOpen, setCreateReturnOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const view = useViewController({ columns: INVOICE_COLUMNS });
  const processedInvoices = view.apply(invoices);

  const returnsView = useViewController({ columns: RETURN_COLUMNS });
  const processedReturns = returnsView.apply(returns);

  const returnsSummary = useMemo(() => {
    const total = returns.reduce((s, r) => s + (r.total || 0), 0);
    return { count: returns.length, total };
  }, [returns]);

  const handleProcess = async (requestId, data) => {
    try {
      await processRequest.mutateAsync({ id: requestId, data });
      toast.success("Order fulfilled — sale and invoice created.");
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    }
  };

  const handleSendToXero = async (invoiceId, e) => {
    e?.stopPropagation();
    try {
      const res = await syncXero.mutateAsync(invoiceId);
      toast.info(res?.message || "Xero sync queued");
    } catch {
      toast.error("Failed to send to Xero");
    }
  };

  const handleBulkSendToXero = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    try {
      const res = await bulkSyncXero.mutateAsync(ids);
      toast.info(res?.message || `${res?.synced ?? 0} queued for Xero`);
      setSelectedIds(new Set());
    } catch {
      toast.error("Failed to bulk send to Xero");
    }
  };

  const statusSummary = useMemo(() => {
    const groups = { draft: [], approved: [], sent: [], paid: [] };
    invoices.forEach((i) => groups[i.status]?.push(i));
    return Object.entries(groups)
      .filter(([, arr]) => arr.length > 0)
      .map(([status, arr]) => ({
        status,
        count: arr.length,
        total: arr.reduce((s, i) => s + (i.total ?? 0), 0),
      }));
  }, [invoices]);

  return (
    <div className="p-8" data-testid="pos-page">
      <div className="mx-auto w-full max-w-7xl">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Point of Sale</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Process contractor requests, issue materials, and track invoices.
            </p>
          </div>
        </div>

        {/* Process sales section */}
        <section className="mb-10">
          <div className="flex flex-col gap-2 mb-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground">Process Sales</h2>
              <p className="text-sm text-muted-foreground">
                Approve pending requests or start a new direct issue.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.7fr)_minmax(280px,1fr)] gap-6 items-start">
            <Panel className="p-5 md:p-6">
              <PendingRequestsSection
                requests={requests}
                isLoading={requestsLoading}
                error={requestsError ? requestsErr : null}
                onRetry={refetchRequests}
                onProcess={handleProcess}
                isProcessing={processRequest.isPending}
              />
            </Panel>
            <QuickActions
              pendingCount={requests.length}
              onProcessReturn={() => setCreateReturnOpen(true)}
            />
          </div>
        </section>

        {/* Transaction history + invoices */}
        <section>
          <div className="flex flex-col gap-2 mb-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground">Invoices</h2>
              <p className="text-sm text-muted-foreground">
                Every sale creates an invoice automatically. Sync to Xero when ready.
              </p>
            </div>
            <DateRangeFilter value={dateRange} onChange={setDateRange} />
          </div>

          <Panel className="p-5 md:p-6">
            {statusSummary.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {statusSummary.map(({ status, count, total }) => {
                  const cls = {
                    draft: "bg-muted border-border text-foreground",
                    approved: "bg-warning/10 border-warning/30 text-accent",
                    sent: "bg-info/10 border-info/30 text-info",
                    paid: "bg-success/10 border-success/30 text-success",
                  }[status];
                  return (
                    <div key={status} className={`px-3 py-1.5 rounded-lg border text-xs ${cls}`}>
                      <span className="font-semibold">
                        {count} {status}
                      </span>
                      <span className="opacity-60 ml-1">· ${total.toFixed(2)}</span>
                    </div>
                  );
                })}
              </div>
            )}

            <ViewToolbar
              controller={view}
              columns={INVOICE_COLUMNS}
              data={invoices}
              resultCount={processedInvoices.length}
              className="mb-3"
            />

            {selectedIds.size > 0 && (
              <div className="bg-info/10 border border-info/30 rounded-xl p-4 mb-4 flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground">
                  {selectedIds.size} selected
                </span>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
                    Clear
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleBulkSendToXero}
                    disabled={bulkSyncXero.isPending}
                    className="bg-info hover:bg-info text-white gap-1"
                  >
                    <Send className="w-3.5 h-3.5" />
                    {bulkSyncXero.isPending ? "Sending…" : `Send to Xero (${selectedIds.size})`}
                  </Button>
                </div>
              </div>
            )}

            <DataTable
              data={processedInvoices}
              columns={view.visibleColumns}
              title="Invoices"
              emptyMessage="No invoices in this range"
              emptyIcon={FileText}
              exportable
              exportFilename={`invoices-${format(new Date(), "yyyyMMdd")}.csv`}
              selectedIds={selectedIds}
              onSelectionChange={setSelectedIds}
              onRowClick={(row) => setDetailInvoiceId(row.id)}
              disableSort
              rowActions={(inv) => (
                <button
                  onClick={(e) => handleSendToXero(inv.id, e)}
                  disabled={syncXero.isPending}
                  className="text-xs text-info hover:text-info flex items-center gap-1"
                >
                  <Send className="w-3.5 h-3.5" />
                  Xero
                </button>
              )}
            />
          </Panel>
        </section>

        {/* Returns */}
        <section className="mt-10">
          <div className="flex flex-col gap-2 mb-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground">Returns</h2>
              <p className="text-sm text-muted-foreground">
                Material returns restock inventory and create credit notes automatically.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCreateReturnOpen(true)}
              className="gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Process Return
            </Button>
          </div>

          <Panel className="p-5 md:p-6">
            {returnsSummary.count > 0 && (
              <div className="flex gap-2 mb-4">
                <div className="px-3 py-1.5 rounded-lg border border-destructive/30 bg-destructive/5 text-xs">
                  <span className="font-semibold text-destructive">
                    {returnsSummary.count} return{returnsSummary.count !== 1 ? "s" : ""}
                  </span>
                  <span className="opacity-60 ml-1">· -${returnsSummary.total.toFixed(2)}</span>
                </div>
              </div>
            )}

            <ViewToolbar
              controller={returnsView}
              columns={RETURN_COLUMNS}
              data={returns}
              resultCount={processedReturns.length}
              className="mb-3"
            />

            <DataTable
              data={processedReturns}
              columns={returnsView.visibleColumns}
              title="Returns"
              emptyMessage="No returns in this range"
              emptyIcon={RotateCcw}
              onRowClick={(row) => setDetailReturnId(row.id)}
              disableSort
            />
          </Panel>
        </section>
      </div>

      <InvoiceDetailModal
        invoiceId={detailInvoiceId}
        open={!!detailInvoiceId}
        onOpenChange={(open) => !open && setDetailInvoiceId(null)}
        onSaved={() => {}}
        onDeleted={() => setDetailInvoiceId(null)}
      />

      <ReturnDetailPanel
        returnId={detailReturnId}
        open={!!detailReturnId}
        onOpenChange={(open) => !open && setDetailReturnId(null)}
      />

      <CreateReturnModal open={createReturnOpen} onOpenChange={setCreateReturnOpen} />
    </div>
  );
}

function QuickActions({ pendingCount = 0, onProcessReturn }) {
  return (
    <Panel className="p-5 md:p-6">
      <div className="space-y-5">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Quick Actions
          </p>
          <h3 className="mt-2 text-lg font-semibold text-foreground">New sale</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Issue materials directly or via barcode scanning.
          </p>
        </div>

        {pendingCount > 0 && (
          <div className="rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3">
            <p className="text-sm font-medium text-foreground">
              {pendingCount} pending request{pendingCount !== 1 ? "s" : ""}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Process requests from the queue, or create a manual issue below.
            </p>
          </div>
        )}

        <div className="space-y-3">
          <Link
            to="/pos/issue"
            className="flex w-full items-start gap-3 rounded-2xl border border-border/80 bg-surface px-4 py-4 shadow-soft transition-all hover:border-accent/40 hover:bg-accent/5 text-foreground"
          >
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent/10">
              <ShoppingCart className="w-4 h-4 text-accent" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-sm">New sale</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Add items and charge to a contractor&apos;s account.
              </p>
            </div>
          </Link>

          <Link
            to="/pos/scan"
            className="flex w-full items-start gap-3 rounded-2xl border border-border/60 bg-surface/80 px-4 py-4 text-foreground transition-all hover:border-border hover:bg-muted/40"
          >
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted">
              <ScanBarcode className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-sm">Scan mode</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Barcode scanning at the point of issue.
              </p>
            </div>
          </Link>

          <button
            type="button"
            onClick={onProcessReturn}
            className="flex w-full items-start gap-3 rounded-2xl border border-destructive/20 bg-surface/80 px-4 py-4 text-foreground transition-all hover:border-destructive/40 hover:bg-destructive/5"
          >
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-destructive/10">
              <RotateCcw className="w-4 h-4 text-destructive" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-sm">Process return</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Return items, restock inventory, and issue a credit note.
              </p>
            </div>
          </button>
        </div>
      </div>
    </Panel>
  );
}
