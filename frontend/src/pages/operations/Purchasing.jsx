import { useState, useMemo } from "react";
import { Truck, Upload } from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { usePurchaseOrders } from "@/hooks/usePurchaseOrders";
import { PurchaseOrderList } from "@/components/purchasing/PurchaseOrderList";
import { PurchaseOrderDetail } from "@/components/purchasing/PurchaseOrderDetail";
import { ImportFlow } from "@/components/purchasing/ImportFlow";

/**
 * Unified purchasing page: master-detail layout.
 * Left column: PO list + new import trigger.
 * Right column: PO detail, import flow, or empty state.
 */
export default function Purchasing() {
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedPoId, setSelectedPoId] = useState(null);
  const [showImport, setShowImport] = useState(false);

  const params = useMemo(() => ({ status: statusFilter || undefined }), [statusFilter]);
  const { data: orders = [], isLoading, isError, error, refetch } = usePurchaseOrders(params);

  const selectedPo = orders.find((po) => po.id === selectedPoId) || null;

  const handleSelectPo = (poId) => {
    setSelectedPoId(poId);
    setShowImport(false);
  };

  const handleNewImport = () => {
    setShowImport(true);
    setSelectedPoId(null);
  };

  const handleImportComplete = () => {
    setShowImport(false);
    refetch();
  };

  const handlePoUpdated = () => {
    refetch();
  };

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
    <div className="h-full flex flex-col" data-testid="purchasing-page">
      {/* Page header */}
      <div className="px-8 pt-6 pb-0 shrink-0">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">Purchasing</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Track orders from your suppliers and add deliveries to inventory
        </p>
      </div>

      {/* Master-detail layout */}
      <div className="flex-1 flex min-h-0 mt-4 mx-8 mb-8 rounded-xl border border-border/60 overflow-hidden bg-card shadow-sm">
        {/* Left column: order list */}
        <div className="w-72 shrink-0 border-r border-border/50 bg-surface/50">
          <PurchaseOrderList
            orders={orders}
            selectedId={selectedPoId}
            onSelect={handleSelectPo}
            importActive={showImport}
            onNewImport={handleNewImport}
            statusFilter={statusFilter}
            onFilterChange={setStatusFilter}
          />
        </div>

        {/* Right column: detail / import / empty state */}
        <div className="flex-1 min-w-0">
          {showImport ? (
            <ImportFlow onComplete={handleImportComplete} onCancel={() => setShowImport(false)} />
          ) : selectedPo ? (
            <PurchaseOrderDetail
              po={selectedPo}
              onBack={() => setSelectedPoId(null)}
              onUpdated={handlePoUpdated}
            />
          ) : (
            <EmptyDetail onNewImport={handleNewImport} />
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyDetail({ onNewImport }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center px-8">
      <div className="w-16 h-16 rounded-2xl bg-muted/50 border border-border/50 flex items-center justify-center mb-4">
        <Truck className="w-8 h-8 text-muted-foreground/40" />
      </div>
      <p className="font-medium text-muted-foreground">Select an order to get started</p>
      <p className="text-sm text-muted-foreground/70 mt-1 max-w-sm">
        Choose a purchase order from the list, or add a new one by uploading a receipt or invoice.
      </p>
      <button
        type="button"
        onClick={onNewImport}
        className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg border border-accent/30 bg-accent/5 text-accent text-sm font-medium hover:bg-accent/10 transition-colors"
      >
        <Upload className="w-4 h-4" />
        Add Order
      </button>
    </div>
  );
}
