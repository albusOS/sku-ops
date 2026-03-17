import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Upload, Truck, Package } from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { PageHeader } from "@/components/PageHeader";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { StatusBadge } from "@/components/StatusBadge";
import { useViewController } from "@/hooks/useViewController";
import { usePurchaseOrders } from "@/hooks/usePurchaseOrders";
import { PODetailPanel } from "@/components/purchasing/PODetailPanel";
import { ImportFlow } from "@/components/purchasing/ImportFlow";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";

export default function Purchasing() {
  const [detailPo, setDetailPo] = useState(null);
  const [showImport, setShowImport] = useState(false);

  const { data: orders = [], isLoading, isError, error, refetch } = usePurchaseOrders();

  const columns = useMemo(
    () => [
      {
        key: "vendor_name",
        label: "Vendor",
        type: "text",
        render: (row) => <span className="font-semibold">{row.vendor_name}</span>,
      },
      {
        key: "status",
        label: "Status",
        type: "enum",
        filterValues: [
          { value: "ordered", label: "Ordered" },
          { value: "partial", label: "In Transit" },
          { value: "received", label: "Received" },
        ],
        render: (row) => <StatusBadge status={row.status} className="text-[10px] px-1.5 py-0" />,
        exportValue: (row) => row.status,
      },
      {
        key: "item_count",
        label: "Items",
        type: "number",
        align: "right",
        render: (row) => <span className="font-mono">{row.item_count}</span>,
      },
      {
        key: "_progress",
        label: "Progress",
        sortable: false,
        filterable: false,
        searchable: false,
        align: "right",
        render: (row) => <ProgressPips po={row} />,
        exportValue: (row) => {
          const total = row.item_count || 1;
          const arrived = row.arrived_count || 0;
          return `${arrived}/${total}`;
        },
      },
      {
        key: "total",
        label: "Total",
        type: "number",
        align: "right",
        render: (row) => (
          <span className="font-mono">
            {row.total > 0 ? `$${Number(row.total).toFixed(2)}` : "—"}
          </span>
        ),
        exportValue: (row) => (row.total || 0).toFixed(2),
      },
      {
        key: "created_at",
        label: "Date",
        type: "date",
        align: "right",
        render: (row) => (
          <span className="text-muted-foreground text-xs tabular-nums">
            {new Date(row.created_at).toLocaleDateString()}
          </span>
        ),
        exportValue: (row) => new Date(row.created_at).toLocaleDateString(),
      },
    ],
    [],
  );

  const view = useViewController({ columns });
  const processedOrders = view.apply(orders);

  const panelOpen = !!detailPo;

  const stats = useMemo(() => {
    const s = { total: orders.length, spend: 0, inTransit: 0, ordered: 0 };
    for (const po of orders) {
      s.spend += po.total || 0;
      if (po.status === "ordered") s.ordered++;
      else if (po.status === "partial") s.inTransit++;
    }
    return s;
  }, [orders]);

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
    <TooltipProvider delayDuration={300}>
      <div className="h-full flex flex-col" data-testid="purchasing-page">
        {/* Page header */}
        <div className="px-8 pt-8 pb-0 shrink-0">
          <PageHeader
            title="Purchasing"
            subtitle={`${stats.total} orders · $${stats.spend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} total spend`}
            action={
              <Button onClick={() => setShowImport(true)} className="btn-primary h-12 px-6">
                <Upload className="w-5 h-5 mr-2" />
                Add Order
              </Button>
            }
          />
        </div>

        {/* Stats strip */}
        <div className="px-8 shrink-0">
          <div className="grid grid-cols-3 gap-3 mb-4">
            <StatPill
              label="Awaiting Delivery"
              value={stats.ordered}
              icon={Package}
              color={stats.ordered > 0 ? "text-warning" : "text-muted-foreground"}
              highlight={stats.ordered > 0}
            />
            <StatPill
              label="In Transit"
              value={stats.inTransit}
              icon={Truck}
              color={stats.inTransit > 0 ? "text-info" : "text-muted-foreground"}
              highlight={stats.inTransit > 0}
            />
            <StatPill
              label="Total Spend"
              value={`$${stats.spend.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
              icon={Package}
              color="text-foreground"
            />
          </div>
        </div>

        {/* Toolbar */}
        <div className="px-8 shrink-0">
          <ViewToolbar
            controller={view}
            columns={columns}
            data={orders}
            resultCount={processedOrders.length}
          />
        </div>

        {/* Content area — splits when panel is open */}
        <div className="flex-1 flex min-h-0 mt-3">
          {/* Table */}
          <motion.div
            layout
            animate={{ width: panelOpen ? "58%" : "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 36 }}
            className="h-full overflow-auto px-8 pb-8 shrink-0"
          >
            <DataTable
              data={processedOrders}
              columns={view.visibleColumns}
              emptyMessage="No purchase orders yet"
              emptyIcon={Truck}
              onRowClick={(po) => setDetailPo(po)}
              exportable
              exportFilename="purchase-orders.csv"
              disableSort
            />
          </motion.div>

          {/* Detail panel */}
          <AnimatePresence>
            {panelOpen && (
              <motion.div
                key="panel"
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: "42%", opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 36 }}
                className="h-full shrink-0 overflow-hidden"
              >
                <PODetailPanel
                  po={detailPo}
                  open={panelOpen}
                  onClose={() => setDetailPo(null)}
                  onUpdated={refetch}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Import sheet */}
        <Sheet open={showImport} onOpenChange={setShowImport}>
          <SheetContent side="right" className="sm:max-w-lg w-full p-0 overflow-hidden">
            <SheetHeader className="sr-only">
              <SheetTitle>Add Purchase Order</SheetTitle>
              <SheetDescription>
                Upload a vendor bill, receipt, or packing slip to create a purchase order
              </SheetDescription>
            </SheetHeader>
            <ImportFlow
              onComplete={() => {
                setShowImport(false);
                refetch();
              }}
              onCancel={() => setShowImport(false)}
            />
          </SheetContent>
        </Sheet>
      </div>
    </TooltipProvider>
  );
}

function ProgressPips({ po }) {
  const total = po.item_count || 1;
  const arrived = po.arrived_count || 0;
  const pending = po.pending_count || 0;

  const arrivedPct = (arrived / total) * 100;
  const pendingPct = (pending / total) * 100;

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden flex min-w-[60px]">
        {arrivedPct > 0 && (
          <div className="h-full bg-success transition-all" style={{ width: `${arrivedPct}%` }} />
        )}
        {pendingPct > 0 && (
          <div className="h-full bg-info transition-all" style={{ width: `${pendingPct}%` }} />
        )}
      </div>
      <span className="text-[10px] tabular-nums text-muted-foreground whitespace-nowrap">
        {arrived}/{total}
      </span>
    </div>
  );
}

function StatPill({ label, value, icon: Icon, color, highlight }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-xl border border-border/60 bg-card/70 px-4 py-2.5 shadow-sm ${
        highlight ? "ring-1 ring-info/20" : ""
      }`}
    >
      <div
        className={`w-8 h-8 rounded-lg bg-muted/60 flex items-center justify-center shrink-0 ${color}`}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-base font-bold tabular-nums leading-none">{value}</p>
        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide mt-0.5">
          {label}
        </p>
      </div>
    </div>
  );
}
