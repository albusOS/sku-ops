import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { SlidersHorizontal, Package, AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { PageHeader } from "@/components/PageHeader";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { StockHistoryModal } from "@/components/StockHistoryModal";
import { useProducts } from "@/hooks/useProducts";
import { useDepartments } from "@/hooks/useDepartments";
import { useViewController } from "@/hooks/useViewController";
import { AdjustStockDialog } from "./AdjustStockDialog";
import { InventoryDetailPanel } from "./InventoryDetailPanel";

function StockBar({ quantity, minStock }) {
  const max = Math.max(minStock * 2, quantity, 1);
  const pct = Math.min((quantity / max) * 100, 100);
  const color =
    quantity === 0 ? "bg-destructive" : quantity <= minStock ? "bg-warning" : "bg-success";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden min-w-[48px]">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums whitespace-nowrap">{quantity}</span>
    </div>
  );
}

const SPRING = { type: "spring", stiffness: 300, damping: 36 };

const InventoryPage = () => {
  const [detailProduct, setDetailProduct] = useState(null);
  const [stockHistoryProduct, setStockHistoryProduct] = useState(null);
  const [adjustProduct, setAdjustProduct] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const {
    data: productsData,
    isLoading: productsLoading,
    isError: productsError,
    error: productsErr,
    refetch: refetchProducts,
  } = useProducts({ limit: 500 });
  const { data: departments = [], isLoading: deptsLoading } = useDepartments();

  const allProducts = useMemo(
    () => productsData?.items ?? (Array.isArray(productsData) ? productsData : []),
    [productsData],
  );
  const loading = productsLoading || deptsLoading;

  const columns = useMemo(
    () => [
      {
        key: "sku",
        label: "SKU",
        type: "text",
        render: (row) => <span className="font-mono text-sm">{row.sku}</span>,
      },
      {
        key: "name",
        label: "Product",
        type: "text",
        render: (row) => (
          <div>
            <p className="font-semibold">{row.name}</p>
            <p className="text-xs text-muted-foreground">{row.category_name}</p>
          </div>
        ),
      },
      {
        key: "quantity",
        label: "Stock",
        type: "number",
        align: "right",
        render: (row) => <StockBar quantity={row.quantity ?? 0} minStock={row.min_stock ?? 5} />,
        exportValue: (row) => `${row.quantity} ${row.base_unit || "ea"}`,
      },
      {
        key: "min_stock",
        label: "Reorder At",
        type: "number",
        align: "right",
        render: (row) => (
          <span className="font-mono text-xs text-muted-foreground">
            {row.min_stock ?? 5} {row.base_unit || "ea"}
          </span>
        ),
      },
      {
        key: "_status",
        label: "Status",
        type: "enum",
        filterValues: ["In Stock", "Low Stock", "Out of Stock"],
        filterAccessor: (row) =>
          row.quantity === 0
            ? "Out of Stock"
            : row.quantity <= (row.min_stock ?? 5)
              ? "Low Stock"
              : "In Stock",
        searchable: false,
        render: (row) =>
          row.quantity === 0 ? (
            <span className="badge-error">Out of Stock</span>
          ) : row.quantity <= (row.min_stock ?? 5) ? (
            <span className="badge-warning">Low Stock</span>
          ) : (
            <span className="badge-success">In Stock</span>
          ),
        exportValue: (row) =>
          row.quantity === 0
            ? "Out of Stock"
            : row.quantity <= (row.min_stock ?? 5)
              ? "Low Stock"
              : "In Stock",
      },
      {
        key: "category_name",
        label: "Category",
        type: "enum",
        filterValues: departments.map((d) => d.name),
      },
    ],
    [departments],
  );

  const view = useViewController({ columns });
  const processedProducts = view.apply(allProducts);

  const stats = useMemo(() => {
    let outOfStock = 0;
    let lowStock = 0;
    let inStock = 0;
    for (const p of allProducts) {
      if (p.quantity === 0) outOfStock++;
      else if (p.quantity <= (p.min_stock ?? 5)) lowStock++;
      else inStock++;
    }
    return { outOfStock, lowStock, inStock, total: allProducts.length };
  }, [allProducts]);

  const panelOpen = !!detailProduct;

  if (loading) return <PageSkeleton />;
  if (productsError) return <QueryError error={productsErr} onRetry={refetchProducts} />;

  return (
    <div className="h-full flex flex-col" data-testid="inventory-page">
      <div className="px-8 pt-8 pb-0 shrink-0">
        <PageHeader title="Stock Levels" subtitle={`${stats.total} SKUs tracked`} />
      </div>

      {/* Stats strip */}
      <div className="px-8 shrink-0">
        <div className="grid grid-cols-3 gap-3 mb-4">
          <StatPill
            label="Out of Stock"
            value={stats.outOfStock}
            icon={XCircle}
            color={stats.outOfStock > 0 ? "text-destructive" : "text-muted-foreground"}
            highlight={stats.outOfStock > 0}
          />
          <StatPill
            label="Low Stock"
            value={stats.lowStock}
            icon={AlertTriangle}
            color={stats.lowStock > 0 ? "text-warning" : "text-muted-foreground"}
            highlight={stats.lowStock > 0}
          />
          <StatPill label="In Stock" value={stats.inStock} icon={Package} color="text-success" />
        </div>
      </div>

      {/* Toolbar */}
      <div className="px-8 shrink-0">
        <ViewToolbar
          controller={view}
          columns={columns}
          data={allProducts}
          resultCount={processedProducts.length}
        />
      </div>

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="mx-8 mt-3 shrink-0 flex items-center gap-3 rounded-lg border border-border bg-muted px-4 py-2.5">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 ml-auto"
            onClick={() => {
              const first = processedProducts.find((p) => selectedIds.has(p.id));
              if (first) setAdjustProduct(first);
            }}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            Adjust Stock
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground"
            onClick={() => setSelectedIds(new Set())}
          >
            Deselect
          </Button>
        </div>
      )}

      {/* Content area — splits when panel is open */}
      <div className="flex-1 flex min-h-0 mt-3">
        <motion.div
          layout
          animate={{ width: panelOpen ? "58%" : "100%" }}
          transition={SPRING}
          className="h-full overflow-auto px-8 pb-8 shrink-0"
        >
          <DataTable
            data={processedProducts}
            columns={view.visibleColumns}
            emptyMessage="No products found"
            emptyIcon={Package}
            onRowClick={(p) => setDetailProduct(p)}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            exportable
            exportFilename="stock-levels.csv"
            disableSort
          />
        </motion.div>

        {/* Inline detail panel */}
        <AnimatePresence>
          {panelOpen && (
            <InventoryDetailPanel
              product={detailProduct}
              open={panelOpen}
              onClose={() => setDetailProduct(null)}
              onAdjust={(p) => setAdjustProduct(p)}
              onViewHistory={(p) => setStockHistoryProduct(p)}
            />
          )}
        </AnimatePresence>
      </div>

      <AdjustStockDialog
        product={adjustProduct}
        open={!!adjustProduct}
        onOpenChange={(open) => !open && setAdjustProduct(null)}
      />

      <StockHistoryModal
        product={stockHistoryProduct}
        open={!!stockHistoryProduct}
        onOpenChange={(open) => !open && setStockHistoryProduct(null)}
      />
    </div>
  );
};

export default InventoryPage;

function StatPill({ label, value, icon: Icon, color, highlight }) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border border-border/60 bg-card/70 px-4 py-2.5 shadow-sm",
        highlight && "ring-1 ring-warning/20",
      )}
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
