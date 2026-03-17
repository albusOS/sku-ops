import { useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Plus, Printer, Package, LayoutGrid, LayoutList } from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { PageHeader } from "@/components/PageHeader";
import { StockHistoryModal } from "@/components/StockHistoryModal";
import { BarcodeLabelsModal } from "@/components/BarcodeLabelsModal";
import { ProductDetailPanel } from "@/components/ProductDetailPanel";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { useProducts, useDeleteProduct } from "@/hooks/useProducts";
import { useDepartments } from "@/hooks/useDepartments";
import { useViewController } from "@/hooks/useViewController";
import { getErrorMessage } from "@/lib/api-client";
import { toast } from "sonner";
import { ProductFormDialog } from "./ProductFormDialog";
import { AdjustStockDialog } from "./AdjustStockDialog";
import { StockBadge } from "@/components/StatusBadge";

function ProductCard({ product, selected, onClick }) {
  const isLow = product.quantity > 0 && product.quantity <= (product.min_stock ?? 5);
  const isOut = product.quantity === 0;

  return (
    <motion.button
      layout
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94 }}
      transition={{ duration: 0.18 }}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick(product)}
      className={`
        group relative text-left w-full rounded-2xl border p-4 transition-colors cursor-pointer
        bg-card hover:bg-card/80
        ${
          selected
            ? "border-accent shadow-[0_0_0_1px_hsl(var(--accent)/0.5)] ring-1 ring-accent/30"
            : "border-border/60 hover:border-accent/30"
        }
      `}
    >
      <div
        className={`absolute top-0 left-4 right-4 h-0.5 rounded-b-full transition-colors ${
          isOut ? "bg-destructive" : isLow ? "bg-warning" : "bg-success"
        }`}
      />

      <div className="flex items-start justify-between gap-2 mt-1">
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-sm leading-tight truncate">{product.name}</p>
          <p className="font-mono text-xs text-muted-foreground mt-0.5">{product.sku}</p>
        </div>
        <StockBadge product={product} />
      </div>

      <div className="mt-3 flex items-end justify-between gap-2">
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Price</p>
          <p className="font-mono font-semibold text-sm">${(product.price || 0).toFixed(2)}</p>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Stock</p>
          <p
            className={`font-mono font-semibold text-sm ${isOut ? "text-destructive" : isLow ? "text-warning" : ""}`}
          >
            {product.quantity ?? 0}
          </p>
        </div>
      </div>

      <div className="mt-2">
        <p className="text-[10px] text-muted-foreground truncate">{product.category_name}</p>
      </div>
    </motion.button>
  );
}

const InventoryPage = () => {
  const [searchParams] = useSearchParams();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [detailProduct, setDetailProduct] = useState(null);
  const [stockHistoryProduct, setStockHistoryProduct] = useState(null);
  const [adjustProduct, setAdjustProduct] = useState(null);
  const [labelsModalOpen, setLabelsModalOpen] = useState(false);
  const [labelsProducts, setLabelsProducts] = useState([]);
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, product: null });
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [viewMode, setViewMode] = useState("table");

  const categoryParam = searchParams.get("category");
  const initialFilters = useMemo(
    () => (categoryParam ? { category_name: categoryParam } : {}),
    [], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const deleteMutation = useDeleteProduct();

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
        label: "Product Name",
        type: "text",
        render: (row) => <p className="font-semibold">{row.name}</p>,
      },
      {
        key: "category_name",
        label: "Category",
        type: "enum",
        filterValues: departments.map((d) => d.name),
      },
      {
        key: "base_unit",
        label: "Unit",
        sortable: false,
        filterable: false,
        render: (row) => (
          <span className="text-sm text-muted-foreground">
            {row.base_unit || "each"}
            {row.sell_uom && row.sell_uom !== row.base_unit && (
              <span className="block text-xs text-muted-foreground">
                sell: {row.sell_uom}
                {(row.pack_qty || 1) > 1 ? ` ×${row.pack_qty}` : ""}
              </span>
            )}
          </span>
        ),
      },
      {
        key: "price",
        label: "Price",
        type: "number",
        align: "right",
        render: (row) => <span className="font-mono">${row.price.toFixed(2)}</span>,
        exportValue: (row) => row.price.toFixed(2),
      },
      {
        key: "cost",
        label: "Cost",
        type: "number",
        align: "right",
        render: (row) => (
          <span className="font-mono text-muted-foreground">${(row.cost || 0).toFixed(2)}</span>
        ),
        exportValue: (row) => (row.cost || 0).toFixed(2),
      },
      {
        key: "quantity",
        label: "Quantity",
        type: "number",
        align: "right",
        render: (row) => <span className="font-mono">{row.quantity}</span>,
      },
      {
        key: "created_at",
        label: "Added",
        type: "date",
        align: "right",
        render: (row) =>
          row.created_at ? (
            <span className="text-xs text-muted-foreground tabular-nums">
              {new Date(row.created_at).toLocaleDateString()}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          ),
        exportValue: (row) => (row.created_at ? new Date(row.created_at).toLocaleDateString() : ""),
      },
      {
        key: "_status",
        label: "Status",
        type: "enum",
        filterValues: ["In Stock", "Low Stock", "Out of Stock"],
        filterAccessor: (row) =>
          row.quantity === 0
            ? "Out of Stock"
            : row.quantity <= row.min_stock
              ? "Low Stock"
              : "In Stock",
        searchable: false,
        render: (row) =>
          row.quantity === 0 ? (
            <span className="badge-error">Out of Stock</span>
          ) : row.quantity <= row.min_stock ? (
            <span className="badge-warning">Low Stock</span>
          ) : (
            <span className="badge-success">In Stock</span>
          ),
        exportValue: (row) =>
          row.quantity === 0
            ? "Out of Stock"
            : row.quantity <= row.min_stock
              ? "Low Stock"
              : "In Stock",
      },
    ],
    [departments],
  );

  const view = useViewController({ columns, initialFilters });
  const processedProducts = view.apply(allProducts);

  const openDialog = (product = null) => {
    setEditingProduct(product);
    setDialogOpen(true);
  };

  const handleDeleteClick = (product) => {
    setDeleteConfirm({ open: true, product });
  };

  const handleDeleteConfirm = async () => {
    const { product } = deleteConfirm;
    if (!product) return;
    try {
      await deleteMutation.mutateAsync(product.id);
      toast.success("Product deleted");
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    }
  };

  if (loading) return <PageSkeleton />;
  if (productsError) return <QueryError error={productsErr} onRetry={refetchProducts} />;

  return (
    <div className="h-full flex flex-col" data-testid="inventory-page">
      <div className="px-8 pt-8 pb-0 shrink-0">
        <PageHeader
          title="Products"
          subtitle={`${allProducts.length} products`}
          action={
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  const source =
                    selectedIds.size > 0
                      ? processedProducts.filter((p) => selectedIds.has(p.id))
                      : processedProducts;
                  setLabelsProducts(source);
                  setLabelsModalOpen(true);
                }}
                className="h-12 px-6"
              >
                <Printer className="w-5 h-5 mr-2" />
                Print Labels
                {selectedIds.size > 0 && ` (${selectedIds.size})`}
              </Button>
              <Button
                onClick={() => openDialog()}
                className="btn-primary h-12 px-6"
                data-testid="add-product-btn"
              >
                <Plus className="w-5 h-5 mr-2" />
                Add Product
              </Button>
            </div>
          }
        />
      </div>

      <div className="px-8 pt-4 shrink-0 flex items-center gap-2">
        <ViewToolbar
          controller={view}
          columns={columns}
          data={allProducts}
          resultCount={processedProducts.length}
          className="flex-1"
        />
        <div className="flex items-center rounded-lg border border-border bg-muted/40 p-0.5 shrink-0">
          <button
            onClick={() => setViewMode("table")}
            className={`p-1.5 rounded-md transition-colors ${viewMode === "table" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            title="Table view"
          >
            <LayoutList className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={`p-1.5 rounded-md transition-colors ${viewMode === "grid" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            title="Grid view"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
        </div>
      </div>

      {selectedIds.size > 0 && (
        <div className="mx-8 mt-3 shrink-0 flex items-center gap-3 rounded-lg border border-border bg-muted px-4 py-2.5">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground ml-auto"
            onClick={() => setSelectedIds(new Set())}
          >
            Deselect
          </Button>
        </div>
      )}

      <div className="flex-1 min-h-0 mt-3 px-8 pb-8 overflow-auto">
        {viewMode === "table" ? (
          <DataTable
            data={processedProducts}
            columns={view.visibleColumns}
            emptyMessage="No products found"
            emptyIcon={Package}
            onRowClick={(p) => setDetailProduct(p)}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            exportable
            exportFilename="inventory.csv"
            disableSort
          />
        ) : (
          <AnimatePresence mode="popLayout">
            {processedProducts.length === 0 ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-24 gap-3"
              >
                <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center">
                  <Package className="w-7 h-7 text-muted-foreground" />
                </div>
                <p className="text-sm text-muted-foreground">No products found</p>
              </motion.div>
            ) : (
              <motion.div
                key="grid"
                className="grid gap-3"
                style={{
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                }}
              >
                {processedProducts.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    selected={detailProduct?.id === product.id}
                    onClick={setDetailProduct}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>

      <ProductDetailPanel
        product={detailProduct}
        open={!!detailProduct}
        onOpenChange={(open) => !open && setDetailProduct(null)}
        onEdit={(p) => openDialog(p)}
        onAdjust={(p) => setAdjustProduct(p)}
        onDelete={handleDeleteClick}
        onPrintLabels={(prods) => {
          setLabelsProducts(prods);
          setLabelsModalOpen(true);
        }}
        onViewHistory={(p) => setStockHistoryProduct(p)}
      />

      <ProductFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingProduct={editingProduct}
        departments={departments}
      />

      <AdjustStockDialog
        product={adjustProduct}
        open={!!adjustProduct}
        onOpenChange={(open) => !open && setAdjustProduct(null)}
      />

      <BarcodeLabelsModal
        products={labelsProducts}
        open={labelsModalOpen}
        onOpenChange={setLabelsModalOpen}
      />

      <StockHistoryModal
        product={stockHistoryProduct}
        open={!!stockHistoryProduct}
        onOpenChange={(open) => !open && setStockHistoryProduct(null)}
      />

      <ConfirmDialog
        open={deleteConfirm.open}
        onOpenChange={(open) => setDeleteConfirm((p) => ({ ...p, open }))}
        title="Delete product"
        description={
          deleteConfirm.product
            ? `Delete "${deleteConfirm.product.name}"? This cannot be undone.`
            : ""
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleDeleteConfirm}
        variant="danger"
      />
    </div>
  );
};

export default InventoryPage;
