import { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Plus, Printer, Package, ChevronRight, ChevronDown, Layers } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { PageHeader } from "@/components/PageHeader";
import { ViewToolbar } from "@/components/ViewToolbar";
import { BarcodeLabelsModal } from "@/components/BarcodeLabelsModal";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useProducts, useDeleteProduct } from "@/hooks/useProducts";
import { useDepartments } from "@/hooks/useDepartments";
import { useViewController } from "@/hooks/useViewController";
import { getErrorMessage } from "@/lib/api-client";
import { toast } from "sonner";
import { ProductFormDialog } from "./ProductFormDialog";
import { CatalogDetailPanel } from "./CatalogDetailPanel";

function FamilyGroupRows({ group, columns, expanded, onToggle, onRowClick, onAddVariant }) {
  return (
    <>
      <TableRow
        className="hover:bg-muted/60 transition-colors border-b border-border/40 cursor-pointer bg-muted/30"
        onClick={onToggle}
      >
        <TableCell className="px-2 py-2.5">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
        </TableCell>
        <TableCell className="px-3 py-2.5" colSpan={columns.length}>
          <div className="flex items-center gap-3">
            <span className="font-semibold">{group.name}</span>
            <span className="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">
              {group.skus.length} variants
            </span>
            {group.category && (
              <span className="text-xs text-muted-foreground">{group.category}</span>
            )}
            <span className="font-mono text-sm text-muted-foreground ml-auto mr-2">
              ${group.totalValue.toFixed(2)} avg
            </span>
            {onAddVariant && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAddVariant(group.familyId, group.skus[0]?.category_id);
                }}
                className="text-xs text-accent hover:text-accent/80 font-medium flex items-center gap-1 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add variant
              </button>
            )}
          </div>
        </TableCell>
      </TableRow>
      {expanded &&
        group.skus.map((row) => (
          <TableRow
            key={row.id}
            className="hover:bg-muted/60 transition-colors border-b border-border/40 last:border-0 cursor-pointer bg-card"
            onClick={() => onRowClick?.(row)}
          >
            <TableCell className="px-2 py-2.5" />
            {columns.map((col) => (
              <TableCell
                key={col.key}
                className={cn(
                  "px-3 py-2.5 pl-6",
                  col.align === "right" && "text-right pl-3",
                  col.align === "center" && "text-center pl-3",
                  col.cellClassName,
                )}
              >
                {col.render ? col.render(row) : row[col.key]}
              </TableCell>
            ))}
          </TableRow>
        ))}
    </>
  );
}

const SPRING = { type: "spring", stiffness: 300, damping: 36 };

export default function ProductsPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [variantContext, setVariantContext] = useState(null);
  const [detailProduct, setDetailProduct] = useState(null);
  const [labelsModalOpen, setLabelsModalOpen] = useState(false);
  const [labelsProducts, setLabelsProducts] = useState([]);
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, product: null });
  const [expandedFamilies, setExpandedFamilies] = useState(new Set());

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
            {row.sell_uom || row.base_unit || "each"}
            {(row.pack_qty || 1) > 1 && ` ×${row.pack_qty}`}
          </span>
        ),
      },
      {
        key: "price",
        label: "Price",
        type: "number",
        align: "right",
        render: (row) => <span className="font-mono">${row.price.toFixed(2)}</span>,
      },
      {
        key: "cost",
        label: "Cost",
        type: "number",
        align: "right",
        render: (row) => (
          <span className="font-mono text-muted-foreground">${(row.cost || 0).toFixed(2)}</span>
        ),
      },
      {
        key: "_margin",
        label: "Margin",
        sortable: false,
        filterable: false,
        searchable: false,
        align: "right",
        render: (row) => {
          if (!row.price) return <span className="text-muted-foreground">—</span>;
          const m = ((row.price - (row.cost || 0)) / row.price) * 100;
          return (
            <span
              className={cn("font-mono text-sm", m < 20 ? "text-warning" : "text-muted-foreground")}
            >
              {m.toFixed(0)}%
            </span>
          );
        },
      },
    ],
    [departments],
  );

  const view = useViewController({
    columns,
    initialHiddenColumns: ["base_unit", "cost"],
  });
  const processedProducts = view.apply(allProducts);

  const productFamilyGroups = useMemo(() => {
    const byFamily = new Map();
    for (const p of processedProducts) {
      const fid = p.product_family_id || p.id;
      if (!byFamily.has(fid)) byFamily.set(fid, []);
      byFamily.get(fid).push(p);
    }
    return Array.from(byFamily.entries()).map(([familyId, skus]) => {
      const first = skus[0];
      const avgPrice = skus.reduce((s, sk) => s + (sk.price || 0), 0) / skus.length;
      return {
        familyId,
        name: first.name,
        category: first.category_name,
        skus,
        totalValue: avgPrice,
        isMulti: skus.length > 1,
      };
    });
  }, [processedProducts]);

  const stats = useMemo(() => {
    const families = productFamilyGroups.length;
    const skus = allProducts.length;
    const categories = new Set(allProducts.map((p) => p.category_name).filter(Boolean)).size;
    return { families, skus, categories };
  }, [productFamilyGroups, allProducts]);

  const toggleFamily = useCallback((familyId) => {
    setExpandedFamilies((prev) => {
      const next = new Set(prev);
      if (next.has(familyId)) next.delete(familyId);
      else next.add(familyId);
      return next;
    });
  }, []);

  const openDialog = (product = null, familyCtx = null) => {
    setEditingProduct(product);
    setVariantContext(familyCtx);
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
      if (detailProduct?.id === product.id) setDetailProduct(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    }
  };

  const panelOpen = !!detailProduct;

  if (loading) return <PageSkeleton />;
  if (productsError) return <QueryError error={productsErr} onRetry={refetchProducts} />;

  return (
    <div className="h-full flex flex-col" data-testid="products-page">
      <div className="px-8 pt-8 pb-0 shrink-0">
        <PageHeader
          title="Products"
          subtitle={`${stats.families} families · ${stats.skus} SKUs · ${stats.categories} categories`}
          action={
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setLabelsProducts(processedProducts);
                  setLabelsModalOpen(true);
                }}
                className="h-12 px-6"
              >
                <Printer className="w-5 h-5 mr-2" />
                Print Labels
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

      {/* Stats strip */}
      <div className="px-8 shrink-0">
        <div className="grid grid-cols-3 gap-3 mb-4">
          <StatPill label="Product Families" value={stats.families} icon={Layers} />
          <StatPill label="Total SKUs" value={stats.skus} icon={Package} />
          <StatPill
            label="Categories"
            value={stats.categories}
            icon={Package}
            color="text-muted-foreground"
          />
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

      {/* Content area — splits when panel is open */}
      <div className="flex-1 flex min-h-0 mt-3">
        <motion.div
          layout
          animate={{ width: panelOpen ? "58%" : "100%" }}
          transition={SPRING}
          className="h-full overflow-auto px-8 pb-8 shrink-0"
        >
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/80 hover:bg-muted/80">
                    <TableHead className="w-8 px-2" />
                    {view.visibleColumns.map((col) => (
                      <TableHead
                        key={col.key}
                        className={cn(
                          "text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground px-3 py-2.5",
                          col.align === "right" && "text-right",
                          col.align === "center" && "text-center",
                          col.className,
                        )}
                      >
                        {col.label}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {productFamilyGroups.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={view.visibleColumns.length + 1}
                        className="text-center py-12 text-muted-foreground text-sm"
                      >
                        No products found
                      </TableCell>
                    </TableRow>
                  ) : (
                    productFamilyGroups.map((group) => {
                      const expanded = expandedFamilies.has(group.familyId);
                      if (!group.isMulti) {
                        const row = group.skus[0];
                        return (
                          <TableRow
                            key={row.id}
                            className={cn(
                              "hover:bg-muted/60 transition-colors border-b border-border/40 last:border-0 cursor-pointer",
                              detailProduct?.id === row.id && "bg-accent/5",
                            )}
                            onClick={() => setDetailProduct(row)}
                          >
                            <TableCell className="px-2 py-2.5" />
                            {view.visibleColumns.map((col) => (
                              <TableCell
                                key={col.key}
                                className={cn(
                                  "px-3 py-2.5",
                                  col.align === "right" && "text-right",
                                  col.align === "center" && "text-center",
                                  col.cellClassName,
                                )}
                              >
                                {col.render ? col.render(row) : row[col.key]}
                              </TableCell>
                            ))}
                          </TableRow>
                        );
                      }
                      return (
                        <FamilyGroupRows
                          key={group.familyId}
                          group={group}
                          columns={view.visibleColumns}
                          expanded={expanded}
                          onToggle={() => toggleFamily(group.familyId)}
                          onRowClick={(p) => setDetailProduct(p)}
                          onAddVariant={(familyId, categoryId) =>
                            openDialog(null, { familyId, categoryId })
                          }
                        />
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </motion.div>

        {/* Inline detail panel */}
        <CatalogDetailPanel
          product={detailProduct}
          open={panelOpen}
          onClose={() => setDetailProduct(null)}
          onEdit={(p) => openDialog(p)}
          onDelete={handleDeleteClick}
          onPrintLabels={(prods) => {
            setLabelsProducts(prods);
            setLabelsModalOpen(true);
          }}
          onAddVariant={(familyId, categoryId) => openDialog(null, { familyId, categoryId })}
          onSelectProduct={(p) => setDetailProduct(p)}
        />
      </div>

      <ProductFormDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setVariantContext(null);
        }}
        editingProduct={editingProduct}
        departments={departments}
        variantContext={variantContext}
      />

      <BarcodeLabelsModal
        products={labelsProducts}
        open={labelsModalOpen}
        onOpenChange={setLabelsModalOpen}
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
}

function StatPill({ label, value, icon: Icon, color = "text-foreground" }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-card/70 px-4 py-2.5 shadow-sm">
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
