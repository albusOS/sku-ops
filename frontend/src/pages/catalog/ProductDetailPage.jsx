import { useState, useMemo, useEffect } from "react";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import {
  ChevronRight,
  Package,
  Pencil,
  Trash2,
  Star,
  Truck,
  Printer,
  Tag,
  Settings2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { BarcodeLabelsModal } from "@/components/BarcodeLabelsModal";
import { CategoryCombobox } from "@/components/CategoryCombobox";
import { UnitCombobox } from "@/components/UnitCombobox";
import { EditableField, ReadField } from "@/components/EditableField";
import {
  useProductFamily,
  useProduct,
  useUpdateProduct,
  useDeleteProduct,
  useVendorItems,
  useRemoveVendorItem,
  useSetPreferredVendor,
} from "@/hooks/useProducts";
import { getErrorMessage } from "@/lib/api-client";
import { toast } from "sonner";
import { ProductFormDialog } from "./ProductFormDialog";
import { VariantCard, AddVariantCard } from "./VariantCard";
import { useDepartments } from "@/hooks/useDepartments";

export default function ProductDetailPage() {
  const { familyId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const {
    data: familyData,
    isLoading: familyLoading,
    isError: familyError,
    error: familyErr,
    refetch: refetchFamily,
  } = useProductFamily(familyId);

  const isFamilyFound = !!familyData?.id;

  const {
    data: standaloneSku,
    isLoading: skuLoading,
    isError: skuError,
    error: skuErr,
    refetch: refetchSku,
  } = useProduct(!familyLoading && !isFamilyFound ? familyId : null);

  const isLoading = familyLoading || (!isFamilyFound && skuLoading);
  const isError = familyError && skuError;
  const error = familyErr || skuErr;
  const refetch = isFamilyFound ? refetchFamily : refetchSku;

  const family = useMemo(
    () =>
      isFamilyFound
        ? familyData
        : standaloneSku
          ? {
              id: standaloneSku.id,
              name: standaloneSku.name,
              category_name: standaloneSku.category_name,
              category_id: standaloneSku.category_id,
              skus: [standaloneSku],
            }
          : null,
    [isFamilyFound, familyData, standaloneSku],
  );

  const skus = useMemo(() => family?.skus ?? [], [family]);
  const initialSkuId = searchParams.get("sku");
  const [selectedSkuId, setSelectedSkuId] = useState(initialSkuId);

  useEffect(() => {
    if (initialSkuId) {
      setSelectedSkuId(initialSkuId);
    } else if (skus.length > 0 && !selectedSkuId) {
      setSelectedSkuId(skus[0].id);
    }
  }, [initialSkuId, skus, selectedSkuId]);

  const selectedSku = useMemo(
    () => skus.find((s) => s.id === selectedSkuId) || skus[0] || null,
    [skus, selectedSkuId],
  );

  const isSingleSku = skus.length <= 1;

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [variantContext, setVariantContext] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, product: null });
  const [labelsModalOpen, setLabelsModalOpen] = useState(false);
  const [labelsProducts, setLabelsProducts] = useState([]);

  const { data: departments = [] } = useDepartments();
  const deleteMutation = useDeleteProduct();
  const updateMutation = useUpdateProduct();

  const { data: vendorItems = [], isLoading: vendorsLoading } = useVendorItems(selectedSku?.id);
  const removeVendorItem = useRemoveVendorItem();
  const setPreferred = useSetPreferredVendor();

  const openDialog = (product = null, familyCtx = null) => {
    setEditingProduct(product);
    setVariantContext(familyCtx);
    setDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    const { product } = deleteConfirm;
    if (!product) return;
    try {
      await deleteMutation.mutateAsync(product.id);
      toast.success("Product deleted");
      if (skus.length <= 1) {
        navigate("/products");
      } else {
        setSelectedSkuId(skus.find((s) => s.id !== product.id)?.id || null);
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const handleCategoryChange = (categoryId) => {
    if (!selectedSku) return;
    updateMutation.mutate(
      { id: selectedSku.id, data: { category_id: categoryId } },
      {
        onSuccess: () => toast.success("Category updated"),
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  const handleUnitChange = (field, value) => {
    if (!selectedSku) return;
    updateMutation.mutate(
      { id: selectedSku.id, data: { [field]: value } },
      {
        onSuccess: () => toast.success("Unit updated"),
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;
  if (!family)
    return (
      <QueryError
        error={{ message: "Product family not found" }}
        onRetry={() => navigate("/products")}
      />
    );

  const margin =
    selectedSku?.price > 0
      ? (((selectedSku.price - (selectedSku.cost || 0)) / selectedSku.price) * 100).toFixed(1)
      : null;

  const hasBarcode = (selectedSku?.barcode || selectedSku?.sku)?.toString().trim();

  return (
    <div className="h-full flex flex-col" data-testid="product-detail-page">
      {/* Breadcrumb + actions */}
      <div className="px-8 pt-6 pb-0 shrink-0">
        <div className="flex items-center justify-between">
          <nav className="flex items-center gap-1.5 text-sm">
            <Link
              to="/products"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Products
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="font-medium truncate max-w-[300px]">{family.name}</span>
          </nav>

          <div className="flex items-center gap-2">
            {selectedSku && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 h-8"
                  onClick={() => openDialog(selectedSku)}
                >
                  <Pencil className="w-3.5 h-3.5" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 h-8 text-destructive hover:text-destructive"
                  onClick={() => setDeleteConfirm({ open: true, product: selectedSku })}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Header */}
        <div className="mt-4 flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
            <Package className="w-5 h-5 text-accent" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-semibold tracking-tight">{family.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              {family.category_name && (
                <Badge variant="outline" className="text-[10px] font-mono">
                  {family.category_name}
                </Badge>
              )}
              <span className="text-sm text-muted-foreground">
                {skus.length} variant{skus.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Variant grid */}
      {!isSingleSku && (
        <div className="px-8 mt-6 shrink-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-3">
            Variants
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
            {skus.map((sku) => (
              <VariantCard
                key={sku.id}
                sku={sku}
                isSelected={sku.id === selectedSku?.id}
                onClick={(s) => setSelectedSkuId(s.id)}
              />
            ))}
            <AddVariantCard
              onClick={() => openDialog(null, { familyId, categoryId: family.category_id })}
            />
          </div>
        </div>
      )}

      {/* Selected variant details */}
      {selectedSku && (
        <div className="flex-1 overflow-auto px-8 mt-6 pb-8">
          {/* Pricing strip */}
          <div className="rounded-xl border border-border/60 bg-card p-4 mb-4">
            <div className="grid grid-cols-3 gap-4">
              <EditableField
                label="Price"
                value={selectedSku.price}
                field="price"
                productId={selectedSku.id}
                type="number"
                prefix="$"
                mono
              />
              <EditableField
                label="Cost"
                value={selectedSku.cost}
                field="cost"
                productId={selectedSku.id}
                type="number"
                prefix="$"
                mono
              />
              <ReadField label="Margin" value={margin ? `${margin}%` : "—"} mono />
            </div>
          </div>

          {/* Tabbed sections */}
          <Tabs defaultValue="details" className="w-full">
            <TabsList className="w-full justify-start bg-transparent border-b border-border rounded-none h-auto p-0 gap-0">
              <TabsTrigger
                value="details"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent data-[state=active]:bg-transparent data-[state=active]:shadow-none px-4 pb-2.5 pt-2 text-sm"
              >
                <Settings2 className="w-3.5 h-3.5 mr-1.5" />
                Details
              </TabsTrigger>
              <TabsTrigger
                value="suppliers"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent data-[state=active]:bg-transparent data-[state=active]:shadow-none px-4 pb-2.5 pt-2 text-sm"
              >
                <Truck className="w-3.5 h-3.5 mr-1.5" />
                Suppliers
                {vendorItems.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 text-[10px] px-1.5 py-0">
                    {vendorItems.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="labels"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent data-[state=active]:bg-transparent data-[state=active]:shadow-none px-4 pb-2.5 pt-2 text-sm"
              >
                <Tag className="w-3.5 h-3.5 mr-1.5" />
                Labels
              </TabsTrigger>
            </TabsList>

            {/* Details tab */}
            <TabsContent value="details" className="mt-4">
              <div className="rounded-xl border border-border/60 bg-card p-5">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Category</p>
                    <CategoryCombobox
                      value={selectedSku.category_id}
                      onValueChange={handleCategoryChange}
                      disabled={updateMutation.isPending}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Sell Unit</p>
                    <UnitCombobox
                      value={selectedSku.sell_uom || selectedSku.base_unit || "each"}
                      onValueChange={(v) => handleUnitChange("sell_uom", v)}
                      disabled={updateMutation.isPending}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Base Unit</p>
                    <UnitCombobox
                      value={selectedSku.base_unit || "each"}
                      onValueChange={(v) => handleUnitChange("base_unit", v)}
                      disabled={updateMutation.isPending}
                      className="h-8 text-sm"
                    />
                  </div>
                  <ReadField
                    label="Scan Code"
                    value={selectedSku.barcode || selectedSku.sku}
                    mono
                  />
                  {selectedSku.purchase_uom && selectedSku.purchase_uom !== "each" && (
                    <ReadField
                      label="Purchase UOM"
                      value={`${selectedSku.purchase_uom}${(selectedSku.purchase_pack_qty || 1) > 1 ? ` ×${selectedSku.purchase_pack_qty}` : ""}`}
                    />
                  )}
                  <EditableField
                    label="Min Stock"
                    value={selectedSku.min_stock ?? 5}
                    field="min_stock"
                    productId={selectedSku.id}
                    type="number"
                    mono
                  />
                  <ReadField label="SKU Code" value={selectedSku.sku} mono />
                </div>

                {selectedSku.variant_attrs && Object.keys(selectedSku.variant_attrs).length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border/40">
                    <p className="text-xs text-muted-foreground mb-2">Variant Attributes</p>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(selectedSku.variant_attrs).map(([k, v]) => (
                        <span
                          key={k}
                          className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/40 px-2 py-0.5 text-xs"
                        >
                          <span className="text-muted-foreground">{k}:</span>
                          <span className="font-medium">{v}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-4 pt-4 border-t border-border/40">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={() => openDialog(selectedSku)}
                  >
                    <Pencil className="w-3 h-3" />
                    Edit all fields
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* Suppliers tab */}
            <TabsContent value="suppliers" className="mt-4">
              <div className="rounded-xl border border-border/60 bg-card p-5">
                {vendorsLoading ? (
                  <p className="text-sm text-muted-foreground py-4">Loading suppliers...</p>
                ) : vendorItems.length === 0 ? (
                  <div className="flex flex-col items-center py-8 text-muted-foreground">
                    <Truck className="w-8 h-8 mb-2 opacity-30" />
                    <p className="text-sm font-medium">No suppliers linked</p>
                    <p className="text-xs mt-1">Add suppliers to track costs and lead times</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {vendorItems.map((vi) => (
                      <div
                        key={vi.id}
                        className="rounded-lg border border-border/50 p-4 bg-muted/10 hover:bg-muted/20 transition-colors"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="font-medium text-sm truncate">
                              {vi.vendor_name || "Unknown vendor"}
                            </span>
                            {vi.is_preferred && (
                              <Star className="w-4 h-4 text-amber-500 fill-amber-500 shrink-0" />
                            )}
                          </div>
                          <div className="flex gap-1.5 shrink-0">
                            {!vi.is_preferred && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-amber-500"
                                title="Set as preferred"
                                onClick={() =>
                                  setPreferred.mutate(
                                    { skuId: selectedSku.id, itemId: vi.id },
                                    { onSuccess: () => toast.success("Preferred supplier set") },
                                  )
                                }
                              >
                                <Star className="w-3.5 h-3.5" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                              title="Remove supplier"
                              onClick={() =>
                                removeVendorItem.mutate(
                                  { skuId: selectedSku.id, itemId: vi.id },
                                  { onSuccess: () => toast.success("Supplier removed") },
                                )
                              }
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
                          {vi.vendor_sku && (
                            <span>
                              SKU: <span className="font-mono">{vi.vendor_sku}</span>
                            </span>
                          )}
                          <span>
                            Cost: <span className="font-mono">${(vi.cost || 0).toFixed(2)}</span>
                          </span>
                          {vi.purchase_uom !== "each" && (
                            <span>
                              {vi.purchase_uom}
                              {(vi.purchase_pack_qty || 1) > 1 && ` ×${vi.purchase_pack_qty}`}
                            </span>
                          )}
                          {vi.lead_time_days != null && <span>{vi.lead_time_days}d lead time</span>}
                          {vi.moq != null && vi.moq > 1 && <span>MOQ: {vi.moq}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Labels tab */}
            <TabsContent value="labels" className="mt-4">
              <LabelsSection
                sku={selectedSku}
                hasBarcode={hasBarcode}
                onPrintLabels={(products) => {
                  setLabelsProducts(products);
                  setLabelsModalOpen(true);
                }}
              />
            </TabsContent>
          </Tabs>
        </div>
      )}

      <ProductFormDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) {
            setVariantContext(null);
            setEditingProduct(null);
          }
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

function LabelsSection({ sku, hasBarcode, onPrintLabels }) {
  const [printQty, setPrintQty] = useState(1);

  if (!hasBarcode) {
    return (
      <div className="rounded-xl border border-border/60 bg-card p-5">
        <div className="flex flex-col items-center py-6 text-muted-foreground">
          <Tag className="w-8 h-8 mb-2 opacity-30" />
          <p className="text-sm font-medium">No barcode available</p>
          <p className="text-xs mt-1">Add a barcode to this product to print labels</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/60 bg-card p-5">
      <div className="flex items-center gap-3">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Quantity</p>
          <Input
            type="number"
            min={1}
            max={99}
            value={printQty}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              setPrintQty(isNaN(v) ? 1 : Math.min(99, Math.max(1, v)));
            }}
            className="w-20 h-9 text-sm"
          />
        </div>
        <div className="pt-4">
          <Button
            variant="outline"
            className="gap-1.5 h-9"
            onClick={() => {
              const copies = Array.from({ length: Math.max(1, Math.min(99, printQty)) }, () => sku);
              onPrintLabels(copies);
            }}
          >
            <Printer className="w-4 h-4" />
            Print {printQty} label{printQty !== 1 ? "s" : ""}
          </Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground mt-3">
        Code: <span className="font-mono">{sku.barcode || sku.sku}</span>
      </p>
    </div>
  );
}
