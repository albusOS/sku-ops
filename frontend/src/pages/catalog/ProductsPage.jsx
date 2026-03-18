import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  Plus,
  Printer,
  Package,
  ChevronRight,
  ChevronDown,
  ChevronLeft,
  Search,
  X,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { PageHeader } from "@/components/PageHeader";
import { BarcodeLabelsModal } from "@/components/BarcodeLabelsModal";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useProducts, useDeleteProduct } from "@/hooks/useProducts";
import { useDepartments } from "@/hooks/useDepartments";
import { getErrorMessage } from "@/lib/api-client";
import { toast } from "sonner";
import { ProductFormDialog } from "./ProductFormDialog";
import { CatalogDetailPanel } from "./CatalogDetailPanel";

const PAGE_SIZE = 50;
const SPRING = { type: "spring", stiffness: 300, damping: 36 };

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

function FamilyGroupRows({
  group,
  columns,
  expanded,
  onToggle,
  onRowClick,
  onAddVariant,
  selectedId,
}) {
  return (
    <>
      <TableRow
        className="hover:bg-muted/60 transition-colors border-b border-border/40 cursor-pointer bg-muted/30"
        onClick={onToggle}
      >
        <TableCell className="px-2 py-2.5 w-8">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
        </TableCell>
        <TableCell className="px-3 py-2.5" colSpan={columns.length}>
          <div className="flex items-center gap-3">
            <span className="font-semibold">{group.name}</span>
            <Badge variant="secondary" className="text-[10px] font-medium px-1.5 py-0">
              {group.skus.length} variants
            </Badge>
            {group.category && (
              <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0">
                {group.category}
              </Badge>
            )}
            <span className="font-mono text-sm text-muted-foreground ml-auto mr-2">
              ${group.avgPrice.toFixed(2)} avg
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
            className={cn(
              "hover:bg-muted/60 transition-colors border-b border-border/40 last:border-0 cursor-pointer bg-card",
              selectedId === row.id && "bg-accent/5",
            )}
            onClick={() => onRowClick?.(row)}
          >
            <TableCell className="px-2 py-2.5 w-8" />
            {columns.map((col) => (
              <TableCell
                key={col.key}
                className={cn(
                  "px-3 py-2.5 pl-6",
                  col.align === "right" && "text-right pl-3",
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

export default function ProductsPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [variantContext, setVariantContext] = useState(null);
  const [detailProduct, setDetailProduct] = useState(null);
  const [labelsModalOpen, setLabelsModalOpen] = useState(false);
  const [labelsProducts, setLabelsProducts] = useState([]);
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, product: null });
  const [expandedFamilies, setExpandedFamilies] = useState(new Set());

  // Server-side filter state
  const [searchInput, setSearchInput] = useState("");
  const [categoryFilter, setCategoryFilter] = useState(null);
  const [page, setPage] = useState(0);
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  const debouncedSearch = useDebounce(searchInput, 300);
  const searchRef = useRef(null);

  // Reset to page 0 when filters change
  useEffect(() => {
    setPage(0);
  }, [debouncedSearch, categoryFilter]);

  const deleteMutation = useDeleteProduct();
  const { data: departments = [], isLoading: deptsLoading } = useDepartments();

  const queryParams = useMemo(() => {
    const p = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
    if (debouncedSearch) p.search = debouncedSearch;
    if (categoryFilter) p.category_id = categoryFilter;
    return p;
  }, [debouncedSearch, categoryFilter, page]);

  const {
    data: productsData,
    isLoading: productsLoading,
    isError: productsError,
    error: productsErr,
    refetch: refetchProducts,
  } = useProducts(queryParams);

  const products = useMemo(
    () => productsData?.items ?? (Array.isArray(productsData) ? productsData : []),
    [productsData],
  );
  const total = productsData?.total ?? products.length;
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
  const loading = productsLoading && products.length === 0;

  const columns = useMemo(
    () => [
      {
        key: "sku",
        label: "SKU",
        sortable: true,
        render: (row) => <span className="font-mono text-sm">{row.sku}</span>,
      },
      {
        key: "name",
        label: "Product Name",
        sortable: true,
        render: (row) => <p className="font-semibold">{row.name}</p>,
      },
      {
        key: "category_name",
        label: "Category",
        sortable: true,
        render: (row) => (
          <Badge variant="outline" className="font-mono text-[10px] font-medium px-1.5 py-0">
            {row.category_name}
          </Badge>
        ),
      },
      {
        key: "price",
        label: "Price",
        sortable: true,
        align: "right",
        render: (row) => <span className="font-mono">${row.price.toFixed(2)}</span>,
      },
      {
        key: "cost",
        label: "Cost",
        sortable: true,
        align: "right",
        render: (row) => (
          <span className="font-mono text-muted-foreground">${(row.cost || 0).toFixed(2)}</span>
        ),
      },
      {
        key: "_margin",
        label: "Margin",
        sortable: false,
        align: "right",
        render: (row) => {
          if (!row.price) return <span className="text-muted-foreground">--</span>;
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
    [],
  );

  // Client-side sort on current page (server handles search/filter/pagination)
  const sortedProducts = useMemo(() => {
    if (!sortCol) return products;
    return [...products].sort((a, b) => {
      const va = a[sortCol];
      const vb = b[sortCol];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      const cmp =
        typeof va === "number" && typeof vb === "number"
          ? va - vb
          : String(va).localeCompare(String(vb));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [products, sortCol, sortDir]);

  // Group into families for display
  const productFamilyGroups = useMemo(() => {
    const byFamily = new Map();
    for (const p of sortedProducts) {
      const fid = p.product_family_id || p.id;
      if (!byFamily.has(fid)) byFamily.set(fid, []);
      byFamily.get(fid).push(p);
    }
    return Array.from(byFamily.entries()).map(([familyId, skus]) => {
      const first = skus[0];
      const avgPrice = skus.reduce((s, sk) => s + (sk.price || 0), 0) / skus.length;
      return {
        familyId,
        name: first.product_family_name || first.name,
        category: first.category_name,
        skus,
        avgPrice,
        isMulti: skus.length > 1,
      };
    });
  }, [sortedProducts]);

  const toggleFamily = useCallback((familyId) => {
    setExpandedFamilies((prev) => {
      const next = new Set(prev);
      if (next.has(familyId)) next.delete(familyId);
      else next.add(familyId);
      return next;
    });
  }, []);

  const handleSort = useCallback((key) => {
    setSortCol((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        return key;
      }
      setSortDir("asc");
      return key;
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

  const clearFilters = () => {
    setSearchInput("");
    setCategoryFilter(null);
    setPage(0);
  };

  const hasFilters = !!debouncedSearch || !!categoryFilter;
  const panelOpen = !!detailProduct;

  if (loading && deptsLoading) return <PageSkeleton />;
  if (productsError && products.length === 0)
    return <QueryError error={productsErr} onRetry={refetchProducts} />;

  return (
    <div className="h-full flex flex-col" data-testid="products-page">
      <div className="px-8 pt-8 pb-0 shrink-0">
        <PageHeader
          title="Products"
          subtitle={
            hasFilters
              ? `${total} result${total !== 1 ? "s" : ""}`
              : `${total} SKUs across ${departments.length} categories`
          }
          action={
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setLabelsProducts(sortedProducts);
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

      {/* Toolbar: search + category filter */}
      <div className="px-8 mt-4 shrink-0">
        <div className="bg-card border border-border rounded-xl shadow-sm">
          <div className="px-4 py-2.5 flex flex-wrap items-center gap-2.5">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                ref={searchRef}
                type="text"
                placeholder="Search products..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="h-7 pl-8 pr-3 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent w-56"
              />
            </div>

            <div className="w-px h-5 bg-border" />

            {/* Category filter */}
            <Select
              value={categoryFilter || "__all__"}
              onValueChange={(v) => setCategoryFilter(v === "__all__" ? null : v)}
            >
              <SelectTrigger className="h-7 text-xs w-auto min-w-[120px]">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Categories</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept.id} value={dept.id}>
                    <span className="font-mono mr-1">{dept.code}</span> {dept.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex-1" />

            {/* Result count */}
            {hasFilters && (
              <span className="text-xs text-muted-foreground tabular-nums">
                {total} result{total !== 1 ? "s" : ""}
              </span>
            )}

            {/* Loading indicator for background refetch */}
            {productsLoading && products.length > 0 && (
              <span className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            )}

            {hasFilters && (
              <button
                onClick={clearFilters}
                className="h-7 px-2 flex items-center gap-1 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <X className="w-3 h-3" />
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content area */}
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
                    {columns.map((col) => (
                      <TableHead
                        key={col.key}
                        className={cn(
                          "text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground px-3 py-2.5",
                          col.align === "right" && "text-right",
                          col.sortable && "cursor-pointer select-none hover:text-foreground",
                        )}
                        onClick={() => col.sortable && handleSort(col.key)}
                      >
                        <span
                          className={cn(
                            "inline-flex items-center",
                            col.align === "right" && "justify-end w-full",
                          )}
                        >
                          {col.label}
                          {col.sortable && sortCol === col.key && (
                            <span className="ml-1 text-accent">
                              {sortDir === "asc" ? "↑" : "↓"}
                            </span>
                          )}
                        </span>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {productFamilyGroups.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={columns.length + 1}
                        className="text-center py-16 text-muted-foreground"
                      >
                        <Package className="w-8 h-8 mx-auto mb-3 opacity-30" />
                        <p className="text-sm font-medium">
                          {hasFilters ? "No products match your filters" : "No products yet"}
                        </p>
                        {hasFilters && (
                          <button
                            onClick={clearFilters}
                            className="text-xs text-accent hover:underline mt-1"
                          >
                            Clear filters
                          </button>
                        )}
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
                            <TableCell className="px-2 py-2.5 w-8" />
                            {columns.map((col) => (
                              <TableCell
                                key={col.key}
                                className={cn(
                                  "px-3 py-2.5",
                                  col.align === "right" && "text-right",
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
                          columns={columns}
                          expanded={expanded}
                          onToggle={() => toggleFamily(group.familyId)}
                          onRowClick={(p) => setDetailProduct(p)}
                          onAddVariant={(familyId, categoryId) =>
                            openDialog(null, { familyId, categoryId })
                          }
                          selectedId={detailProduct?.id}
                        />
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-border/50">
                <p className="text-xs text-muted-foreground tabular-nums">
                  {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                </p>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page <= 0}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-xs text-muted-foreground tabular-nums min-w-[4rem] text-center">
                    {page + 1} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
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
