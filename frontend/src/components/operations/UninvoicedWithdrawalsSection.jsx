import { useState, useMemo } from "react";
import { FileText } from "lucide-react";
import { format } from "date-fns";
import { valueFormatter } from "@/lib/chartConfig";
import { StatCard } from "@/components/StatCard";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { CreateInvoiceModal } from "@/components/CreateInvoiceModal";
import { WithdrawalDetailPanel } from "@/components/WithdrawalDetailPanel";
import { InvoiceDetailModal } from "@/components/InvoiceDetailModal";
import { JobDetailPanel } from "@/components/JobDetailPanel";
import { useWithdrawals } from "@/hooks/useWithdrawals";
import { useViewController } from "@/hooks/useViewController";
import { buildWithdrawalColumns } from "./withdrawalColumns";

export function UninvoicedWithdrawalsSection({ dateParams, onViewInvoice, onCreateInvoice }) {
  const { data: withdrawals = [], isLoading } = useWithdrawals(dateParams);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [createInvoiceModalOpen, setCreateInvoiceModalOpen] = useState(false);
  const [detailWithdrawalId, setDetailWithdrawalId] = useState(null);
  const [detailInvoiceId, setDetailInvoiceId] = useState(null);
  const [detailJobId, setDetailJobId] = useState(null);

  const uninvoiced = useMemo(() => withdrawals.filter((w) => !w.invoice_id), [withdrawals]);
  const invoiced = useMemo(() => withdrawals.filter((w) => !!w.invoice_id), [withdrawals]);
  const uninvoicedTotal = uninvoiced.reduce((s, w) => s + (w.total || 0), 0);
  const invoicedTotal = invoiced.reduce((s, w) => s + (w.total || 0), 0);

  const columns = useMemo(() => buildWithdrawalColumns(setDetailJobId), [setDetailJobId]);
  const view = useViewController({ columns });
  const processed = view.apply(withdrawals);

  const selectAllUninvoiced = () => {
    setSelectedIds(new Set(uninvoiced.map((w) => w.id)));
  };

  const selectedUninvoicedIds = useMemo(
    () =>
      [...selectedIds].filter((id) => {
        const w = withdrawals.find((x) => x.id === id);
        return w && !w.invoice_id;
      }),
    [selectedIds, withdrawals],
  );

  const handleCreateInvoiceCreated = (inv) => {
    setSelectedIds(new Set());
    setCreateInvoiceModalOpen(false);
    onCreateInvoice?.(inv);
    if (inv?.id) setDetailInvoiceId(inv.id);
  };

  if (isLoading) return null;

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <StatCard
          label="Uninvoiced"
          value={valueFormatter(uninvoicedTotal)}
          accent="amber"
          note={`${uninvoiced.length} withdrawal${uninvoiced.length !== 1 ? "s" : ""}`}
        />
        <StatCard
          label="Invoiced"
          value={valueFormatter(invoicedTotal)}
          accent="blue"
          note={`${invoiced.length} in range`}
        />
      </div>

      <ViewToolbar
        controller={view}
        columns={columns}
        data={withdrawals}
        resultCount={processed.length}
        className="mb-3"
        actions={
          <button
            onClick={selectAllUninvoiced}
            className="text-xs text-accent hover:text-accent font-medium"
          >
            Select All Uninvoiced
          </button>
        }
      />

      {selectedIds.size > 0 && (
        <div className="bg-warning/10 border border-warning/30 rounded-xl p-4 mb-4 flex items-center justify-between">
          <span className="text-sm font-semibold text-accent">{selectedIds.size} selected</span>
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedIds(new Set())}
              className="text-xs text-muted-foreground hover:text-foreground px-2 py-1"
            >
              Clear
            </button>
            {selectedUninvoicedIds.length > 0 && (
              <button
                onClick={() => setCreateInvoiceModalOpen(true)}
                className="inline-flex items-center gap-1 text-xs font-medium text-accent bg-card border border-warning/30 rounded-lg px-3 py-1.5 hover:bg-warning/10"
              >
                <FileText className="w-3.5 h-3.5" />
                Create Invoice ({selectedUninvoicedIds.length})
              </button>
            )}
          </div>
        </div>
      )}

      <DataTable
        data={processed}
        columns={view.visibleColumns}
        title="Withdrawals"
        emptyMessage="No withdrawals in this range"
        exportable
        exportFilename={`withdrawals-${format(new Date(), "yyyyMMdd")}.csv`}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        isSelectable={(row) => !row.invoice_id}
        onRowClick={(row) => setDetailWithdrawalId(row.id)}
        disableSort
      />

      <CreateInvoiceModal
        open={createInvoiceModalOpen}
        onOpenChange={setCreateInvoiceModalOpen}
        onCreated={handleCreateInvoiceCreated}
        preselectedIds={selectedUninvoicedIds}
      />

      <WithdrawalDetailPanel
        withdrawalId={detailWithdrawalId}
        open={!!detailWithdrawalId}
        onOpenChange={(open) => !open && setDetailWithdrawalId(null)}
        onViewInvoice={(invoiceId) => {
          setDetailWithdrawalId(null);
          setDetailInvoiceId(invoiceId);
          onViewInvoice?.(invoiceId);
        }}
        onViewJob={(jobId) => {
          setDetailWithdrawalId(null);
          setDetailJobId(jobId);
        }}
      />

      <InvoiceDetailModal
        invoiceId={detailInvoiceId}
        open={!!detailInvoiceId}
        onOpenChange={(open) => !open && setDetailInvoiceId(null)}
        onSaved={() => {}}
        onDeleted={() => setDetailInvoiceId(null)}
      />

      <JobDetailPanel
        jobId={detailJobId}
        open={!!detailJobId}
        onOpenChange={(open) => !open && setDetailJobId(null)}
      />
    </>
  );
}
