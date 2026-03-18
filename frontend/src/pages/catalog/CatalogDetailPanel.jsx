import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  X,
  Trash2,
  Printer,
  Package,
  Star,
  Truck,
  Layers,
  Plus,
  ChevronRight,
  Pencil,
  Check,
} from "lucide-react";
import {
  useVendorItems,
  useRemoveVendorItem,
  useSetPreferredVendor,
  useProductFamily,
  useUpdateProduct,
} from "@/hooks/useProducts";
import { useDepartments } from "@/hooks/useDepartments";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/api-client";

function EditableField({ label, value, field, productId, type = "text", prefix, mono, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef(null);
  const updateMutation = useUpdateProduct();

  useEffect(() => {
    setDraft(value);
    setEditing(false);
  }, [value, productId]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const save = () => {
    const parsed = type === "number" ? parseFloat(draft) : draft;
    if (type === "number" && (isNaN(parsed) || parsed < 0)) {
      toast.error(`${label} must be a valid number`);
      setDraft(value);
      setEditing(false);
      return;
    }
    if (parsed === value) {
      setEditing(false);
      return;
    }
    updateMutation.mutate(
      { id: productId, data: { [field]: parsed } },
      {
        onSuccess: () => {
          toast.success(`${label} updated`);
          setEditing(false);
          onSaved?.();
        },
        onError: (err) => {
          toast.error(getErrorMessage(err));
          setDraft(value);
          setEditing(false);
        },
      },
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") save();
    if (e.key === "Escape") {
      setDraft(value);
      setEditing(false);
    }
  };

  if (editing) {
    return (
      <div>
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <div className="flex items-center gap-1.5">
          {prefix && <span className="text-sm text-muted-foreground">{prefix}</span>}
          <Input
            ref={inputRef}
            type={type}
            step={type === "number" ? "0.01" : undefined}
            value={draft ?? ""}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={save}
            onKeyDown={handleKeyDown}
            className="h-8 text-sm font-mono"
            disabled={updateMutation.isPending}
          />
          <button
            onClick={save}
            className="p-1 rounded text-success hover:bg-success/10 transition-colors shrink-0"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  const display =
    type === "number" && value != null
      ? `${prefix || ""}${Number(value).toFixed(2)}`
      : value || "—";

  return (
    <div
      className="group cursor-pointer rounded-md px-1 -mx-1 py-0.5 hover:bg-muted/60 transition-colors"
      onClick={() => setEditing(true)}
    >
      <p className="text-xs text-muted-foreground flex items-center gap-1">
        {label}
        <Pencil className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
      </p>
      <p className={`text-sm text-foreground mt-0.5 ${mono ? "font-mono tabular-nums" : ""}`}>
        {display}
      </p>
    </div>
  );
}

function ReadField({ label, value, mono }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-sm text-foreground mt-0.5 ${mono ? "font-mono tabular-nums" : ""}`}>
        {value || "—"}
      </p>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
      {children}
    </p>
  );
}

export function CatalogDetailPanel({
  product,
  open,
  onClose,
  onEdit,
  onDelete,
  onPrintLabels,
  onAddVariant,
  onSelectProduct,
}) {
  const [printQty, setPrintQty] = useState(1);

  const { data: vendorItems = [], isLoading: vendorsLoading } = useVendorItems(
    open ? product?.id : null,
  );
  const removeVendorItem = useRemoveVendorItem();
  const setPreferred = useSetPreferredVendor();
  const { data: departments = [] } = useDepartments();
  const updateMutation = useUpdateProduct();

  const familyId = product?.product_family_id;
  const { data: familyData } = useProductFamily(open ? familyId : null);
  const isMultiSkuFamily = (familyData?.skus?.length ?? 0) > 1;
  const siblingSkus = (familyData?.skus ?? []).filter((s) => s.id !== product?.id);

  useEffect(() => {
    if (open && product) setPrintQty(1);
  }, [open, product]);

  const hasBarcode = (product?.barcode || product?.sku)?.toString().trim();

  const handlePrint = () => {
    if (!hasBarcode) return;
    const copies = Array.from({ length: Math.max(1, Math.min(99, printQty)) }, () => product);
    onPrintLabels?.(copies);
  };

  const margin =
    product?.price > 0
      ? (((product.price - (product.cost || 0)) / product.price) * 100).toFixed(1)
      : null;

  const baseUnit = product?.base_unit || "each";
  const sellUom = product?.sell_uom || baseUnit;

  const handleCategoryChange = (categoryId) => {
    updateMutation.mutate(
      { id: product.id, data: { category_id: categoryId } },
      {
        onSuccess: () => toast.success("Category updated"),
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  return (
    <AnimatePresence>
      {open && product && (
        <motion.div
          key="catalog-panel"
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: "42%", opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 36 }}
          className="h-full shrink-0 overflow-hidden"
        >
          <div className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden shadow-xl">
            {/* Header */}
            <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                    <Package className="w-4 h-4 text-accent" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="font-semibold text-sm leading-tight truncate">{product.name}</h2>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">{product.sku}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => onDelete?.(product)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {isMultiSkuFamily && familyData && (
                <div className="flex items-center gap-2 rounded-lg bg-accent/10 border border-accent/20 px-3 py-2 mt-3">
                  <Layers className="w-4 h-4 text-accent shrink-0" />
                  <span className="text-xs text-foreground">
                    Variant of <span className="font-semibold">{familyData.name}</span>
                  </span>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {familyData.skus.length} variants
                  </span>
                </div>
              )}
            </div>

            {/* Single scrollable body — no tabs */}
            <div className="flex-1 overflow-auto px-5 py-4 space-y-5">
              {/* Pricing — inline editable */}
              <div className="space-y-3">
                <SectionLabel>Pricing</SectionLabel>
                <div className="grid grid-cols-3 gap-3">
                  <EditableField
                    label="Price"
                    value={product.price}
                    field="price"
                    productId={product.id}
                    type="number"
                    prefix="$"
                    mono
                  />
                  <EditableField
                    label="Cost"
                    value={product.cost}
                    field="cost"
                    productId={product.id}
                    type="number"
                    prefix="$"
                    mono
                  />
                  <ReadField label="Margin" value={margin ? `${margin}%` : "—"} mono />
                </div>
              </div>

              {/* Product info — mixed editable + read-only */}
              <div className="space-y-3">
                <SectionLabel>Details</SectionLabel>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Category</p>
                    <Select
                      value={product.category_id}
                      onValueChange={handleCategoryChange}
                      disabled={updateMutation.isPending}
                    >
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {departments.map((dept) => (
                          <SelectItem key={dept.id} value={dept.id}>
                            <span className="font-mono text-xs">{dept.code}</span>
                            <span className="text-muted-foreground mx-1">—</span>
                            {dept.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <ReadField
                    label="Sell Unit"
                    value={`${sellUom}${(product.pack_qty || 1) > 1 ? ` ×${product.pack_qty}` : ""}`}
                  />
                  <ReadField label="Base Unit" value={baseUnit} />
                  <ReadField label="Scan Code" value={product.barcode || product.sku} mono />
                  {product.purchase_uom && product.purchase_uom !== "each" && (
                    <ReadField
                      label="Purchase UOM"
                      value={`${product.purchase_uom}${(product.purchase_pack_qty || 1) > 1 ? ` ×${product.purchase_pack_qty}` : ""}`}
                    />
                  )}
                  <EditableField
                    label="Min Stock"
                    value={product.min_stock ?? 5}
                    field="min_stock"
                    productId={product.id}
                    type="number"
                    mono
                  />
                </div>

                {/* Full edit button */}
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full gap-1.5 text-xs mt-1"
                  onClick={() => onEdit?.(product)}
                >
                  <Pencil className="w-3 h-3" />
                  Edit all fields
                </Button>
              </div>

              {/* Variant attributes */}
              {product.variant_attrs && Object.keys(product.variant_attrs).length > 0 && (
                <div className="space-y-3">
                  <SectionLabel>Variant Attributes</SectionLabel>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(product.variant_attrs).map(([k, v]) => (
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

              {/* Sibling variants */}
              {isMultiSkuFamily && siblingSkus.length > 0 && (
                <div className="space-y-3">
                  <SectionLabel>Sibling Variants</SectionLabel>
                  <div className="space-y-1.5">
                    {siblingSkus.map((sibling) => (
                      <button
                        key={sibling.id}
                        onClick={() => onSelectProduct?.(sibling)}
                        className="flex items-center justify-between w-full rounded-lg border border-border/50 bg-muted/20 px-3 py-2 text-left hover:bg-muted/50 transition-colors group"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">{sibling.name}</p>
                          <p className="text-xs text-muted-foreground font-mono">{sibling.sku}</p>
                        </div>
                        <div className="flex items-center gap-3 shrink-0 ml-3">
                          <p className="font-mono text-xs">${(sibling.price || 0).toFixed(2)}</p>
                          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      </button>
                    ))}
                  </div>
                  {onAddVariant && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-1 w-full gap-1.5 text-xs"
                      onClick={() => onAddVariant(familyId, product.category_id)}
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add variant
                    </Button>
                  )}
                </div>
              )}

              {!isMultiSkuFamily && familyId && onAddVariant && (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full gap-1.5 text-xs"
                  onClick={() => onAddVariant(familyId, product.category_id)}
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add variant to this product
                </Button>
              )}

              {/* Suppliers — inline, no tab */}
              <div className="space-y-3">
                <SectionLabel>
                  Suppliers{vendorItems.length > 0 ? ` (${vendorItems.length})` : ""}
                </SectionLabel>
                {vendorsLoading ? (
                  <p className="text-sm text-muted-foreground">Loading...</p>
                ) : vendorItems.length === 0 ? (
                  <div className="flex items-center gap-2 py-4 text-muted-foreground">
                    <Truck className="w-4 h-4 opacity-40" />
                    <p className="text-xs">No suppliers linked</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {vendorItems.map((vi) => (
                      <div
                        key={vi.id}
                        className="rounded-lg border border-border/50 p-3 bg-muted/20"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="font-medium text-sm truncate">
                              {vi.vendor_name || "Unknown vendor"}
                            </span>
                            {vi.is_preferred && (
                              <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500 shrink-0" />
                            )}
                          </div>
                          <div className="flex gap-1 shrink-0">
                            {!vi.is_preferred && (
                              <button
                                className="p-1 text-muted-foreground hover:text-amber-500 rounded-md transition-colors"
                                title="Set as preferred"
                                onClick={() =>
                                  setPreferred.mutate(
                                    { skuId: product.id, itemId: vi.id },
                                    { onSuccess: () => toast.success("Preferred supplier set") },
                                  )
                                }
                              >
                                <Star className="w-3 h-3" />
                              </button>
                            )}
                            <button
                              className="p-1 text-muted-foreground hover:text-destructive rounded-md transition-colors"
                              title="Remove supplier"
                              onClick={() =>
                                removeVendorItem.mutate(
                                  { skuId: product.id, itemId: vi.id },
                                  { onSuccess: () => toast.success("Supplier removed") },
                                )
                              }
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 text-xs text-muted-foreground">
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
                          {vi.lead_time_days != null && <span>{vi.lead_time_days}d lead</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Labels — compact inline */}
              {hasBarcode && (
                <div className="space-y-3">
                  <SectionLabel>Labels</SectionLabel>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={1}
                      max={99}
                      value={printQty}
                      onChange={(e) => {
                        const v = parseInt(e.target.value, 10);
                        setPrintQty(isNaN(v) ? 1 : Math.min(99, Math.max(1, v)));
                      }}
                      className="w-16 h-8 text-sm"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handlePrint}
                      className="gap-1.5 text-xs"
                    >
                      <Printer className="w-3.5 h-3.5" />
                      Print {printQty} label{printQty !== 1 ? "s" : ""}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
