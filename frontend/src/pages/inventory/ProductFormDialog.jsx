import { useState, useEffect, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Sparkles, ChevronDown, Plus, X } from "lucide-react";
import { getErrorMessage } from "@/lib/api-client";
import api from "@/lib/api-client";
import {
  useCreateProduct,
  useUpdateProduct,
  useCreateVariant,
  useSuggestUom,
} from "@/hooks/useProducts";
import { ProductFields } from "@/components/ProductFields";

function VariantAttrsEditor({ attrs, onChange }) {
  const entries = Object.entries(attrs || {});

  const handleKeyChange = (oldKey, newKey) => {
    const next = {};
    for (const [k, v] of Object.entries(attrs)) {
      next[k === oldKey ? newKey : k] = v;
    }
    onChange(next);
  };

  const handleValueChange = (key, value) => {
    onChange({ ...attrs, [key]: value });
  };

  const handleRemove = (key) => {
    const next = { ...attrs };
    delete next[key];
    onChange(next);
  };

  const handleAdd = () => {
    onChange({ ...attrs, "": "" });
  };

  return (
    <div className="space-y-2">
      {entries.map(([k, v], i) => (
        <div key={i} className="flex items-center gap-2">
          <Input
            placeholder="Attribute"
            value={k}
            onChange={(e) => handleKeyChange(k, e.target.value)}
            className="input-workshop flex-1 text-sm"
          />
          <Input
            placeholder="Value"
            value={v}
            onChange={(e) => handleValueChange(k, e.target.value)}
            className="input-workshop flex-1 text-sm"
          />
          <button
            type="button"
            onClick={() => handleRemove(k)}
            className="p-1.5 text-muted-foreground hover:text-destructive rounded-md transition-colors shrink-0"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={handleAdd}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
        Add attribute
      </button>
    </div>
  );
}

const INITIAL_FORM = {
  name: "",
  description: "",
  price: "",
  cost: "",
  quantity: "",
  min_stock: "5",
  category_id: "",
  barcode: "",
  base_unit: "each",
  sell_uom: "each",
  pack_qty: "1",
  purchase_uom: "each",
  purchase_pack_qty: "1",
  variant_attrs: {},
};

const ADVANCED_FIELDS = new Set([
  "description",
  "cost",
  "min_stock",
  "base_unit",
  "sell_uom",
  "pack_qty",
  "purchase_uom",
  "purchase_pack_qty",
  "barcode",
]);

const ESSENTIAL_FIELDS = new Set(["name", "category_id", "price", "quantity"]);

export function ProductFormDialog({
  open,
  onOpenChange,
  editingProduct,
  departments = [],
  variantContext = null,
}) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const suggestTimeout = useRef(null);

  const createMutation = useCreateProduct();
  const updateMutation = useUpdateProduct();
  const variantMutation = useCreateVariant();
  const suggestMutation = useSuggestUom();
  const isVariantMode = !!variantContext?.familyId;
  const saving = createMutation.isPending || updateMutation.isPending || variantMutation.isPending;

  const skuPreviewEnabled = open && !editingProduct && !!form.category_id;
  const { data: skuPreviewData } = useQuery({
    queryKey: ["skuPreview", form.category_id, form.name],
    queryFn: () => {
      const params = { category_id: form.category_id };
      if (form.name?.trim()) params.family_name = form.name.trim();
      return api.sku.preview(params);
    },
    enabled: skuPreviewEnabled,
  });
  const skuPreview = skuPreviewData?.next_sku ?? null;

  useEffect(() => {
    if (!open) return;
    if (editingProduct) {
      setForm({
        name: editingProduct.name,
        description: editingProduct.description || "",
        price: editingProduct.price.toString(),
        cost: editingProduct.cost?.toString() || "",
        quantity: editingProduct.quantity.toString(),
        min_stock: editingProduct.min_stock?.toString() || "5",
        category_id: editingProduct.category_id,
        barcode: editingProduct.barcode || "",
        base_unit: editingProduct.base_unit || "each",
        sell_uom: editingProduct.sell_uom || "each",
        pack_qty: String(editingProduct.pack_qty ?? 1),
        purchase_uom: editingProduct.purchase_uom || "each",
        purchase_pack_qty: String(editingProduct.purchase_pack_qty ?? 1),
        variant_attrs: editingProduct.variant_attrs || {},
      });
      setAdvancedOpen(true);
    } else if (isVariantMode) {
      setForm({ ...INITIAL_FORM, category_id: variantContext.categoryId || "" });
      setAdvancedOpen(false);
    } else {
      setForm(INITIAL_FORM);
      setAdvancedOpen(false);
    }
  }, [open, editingProduct, isVariantMode, variantContext]);

  useEffect(() => {
    return () => {
      if (suggestTimeout.current) clearTimeout(suggestTimeout.current);
    };
  }, []);

  const handleNameChange = useCallback(
    (v) => {
      setForm((f) => ({ ...f, name: v }));
      if (suggestTimeout.current) clearTimeout(suggestTimeout.current);
      if (!editingProduct && v.trim().length >= 3) {
        suggestTimeout.current = setTimeout(() => {
          suggestMutation.mutate(
            { name: v.trim() },
            {
              onSuccess: (data) => {
                setForm((f) => ({
                  ...f,
                  base_unit: data.base_unit || "each",
                  sell_uom: data.sell_uom || "each",
                  pack_qty: String(data.pack_qty ?? 1),
                }));
              },
            },
          );
          suggestTimeout.current = null;
        }, 600);
      }
    },
    [editingProduct, suggestMutation],
  );

  const suggestUnit = useCallback(() => {
    if (!form.name?.trim()) {
      toast.error("Enter a product name first");
      return;
    }
    suggestMutation.mutate(
      {
        name: form.name.trim(),
        description: form.description?.trim() || undefined,
      },
      {
        onSuccess: (data) => {
          setForm((f) => ({
            ...f,
            base_unit: data.base_unit || "each",
            sell_uom: data.sell_uom || "each",
            pack_qty: String(data.pack_qty ?? 1),
          }));
          toast.success("Unit suggested");
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  }, [form.name, form.description, suggestMutation]);

  const handleFieldChange = useCallback(
    (name, value) => {
      if (name === "name") {
        handleNameChange(value);
        return;
      }
      setForm((f) => ({ ...f, [name]: value }));
    },
    [handleNameChange],
  );

  const hasAdvancedValues =
    !!form.description ||
    !!form.cost ||
    !!form.barcode ||
    (form.base_unit && form.base_unit !== "each") ||
    (form.sell_uom && form.sell_uom !== "each") ||
    (form.pack_qty && form.pack_qty !== "1") ||
    (form.min_stock && form.min_stock !== "5");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.price || !form.category_id) {
      toast.error("Please fill in required fields");
      return;
    }
    const price = parseFloat(form.price);
    const cost = parseFloat(form.cost) || 0;
    if (isNaN(price) || price < 0) {
      toast.error("Price must be zero or greater");
      return;
    }
    if (cost < 0) {
      toast.error("Cost must be zero or greater");
      return;
    }

    const baseData = {
      name: form.name,
      description: form.description,
      price,
      cost,
      min_stock: parseInt(form.min_stock) || 5,
      category_id: form.category_id,
      barcode: form.barcode || null,
      base_unit: form.base_unit || "each",
      sell_uom: form.sell_uom || "each",
      pack_qty: parseInt(form.pack_qty) || 1,
      purchase_uom: form.purchase_uom || "each",
      purchase_pack_qty: parseInt(form.purchase_pack_qty) || 1,
      variant_attrs: form.variant_attrs || {},
    };

    // quantity is only included when creating — edits go through AdjustStockDialog
    const data = editingProduct
      ? baseData
      : { ...baseData, quantity: parseFloat(form.quantity) || 0 };

    let mutation, mutationArg;
    if (editingProduct) {
      mutation = updateMutation;
      mutationArg = { id: editingProduct.id, data };
    } else if (isVariantMode) {
      mutation = variantMutation;
      mutationArg = { familyId: variantContext.familyId, data };
    } else {
      mutation = createMutation;
      mutationArg = data;
    }

    mutation.mutate(mutationArg, {
      onSuccess: (result) => {
        toast.success(
          editingProduct
            ? "Product updated!"
            : `${isVariantMode ? "Variant" : "Product"} created with SKU ${result?.sku ?? ""}`,
        );
        onOpenChange(false);
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg rounded-2xl" data-testid="product-dialog">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            {editingProduct ? "Edit product" : isVariantMode ? "Add variant" : "Add new product"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-4">
          <div
            className={`rounded-lg px-4 py-3 ${editingProduct ? "bg-warning/10 border border-warning/30" : "bg-muted border border-border"}`}
          >
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                SKU
              </p>
              {editingProduct && (
                <span className="text-[10px] font-medium text-accent uppercase tracking-wider">
                  Cannot be changed
                </span>
              )}
            </div>
            {editingProduct ? (
              <p className="font-mono text-lg font-semibold text-foreground">
                {editingProduct.sku}
              </p>
            ) : skuPreview ? (
              <p className="font-mono text-lg font-semibold text-foreground">
                {skuPreview}
                <span className="text-xs font-normal text-muted-foreground ml-2">
                  (assigned on save)
                </span>
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">Select a category to see SKU</p>
            )}
          </div>

          {/* Essentials: name, department, price, quantity (quantity hidden when editing) */}
          <ProductFields
            fields={form}
            onChange={handleFieldChange}
            departments={departments}
            hiddenFields={
              editingProduct ? new Set([...ADVANCED_FIELDS, "quantity"]) : ADVANCED_FIELDS
            }
          />

          {editingProduct && (
            <p className="text-xs text-muted-foreground -mt-2">
              To change stock quantity use{" "}
              <span className="font-medium text-foreground">Adjust Stock</span>.
            </p>
          )}

          {/* Advanced: collapsible */}
          <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors w-full"
              >
                <ChevronDown
                  className={`w-3.5 h-3.5 transition-transform ${advancedOpen ? "rotate-0" : "-rotate-90"}`}
                />
                Advanced fields
                {!advancedOpen && hasAdvancedValues && (
                  <span className="w-1.5 h-1.5 rounded-full bg-accent ml-1" />
                )}
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-3 space-y-4">
              <ProductFields
                fields={form}
                onChange={handleFieldChange}
                departments={departments}
                hiddenFields={ESSENTIAL_FIELDS}
                uomAction={
                  <Button
                    type="button"
                    variant="outline"
                    onClick={suggestUnit}
                    disabled={suggestMutation.isPending || !form.name?.trim()}
                    className="h-11 px-3 border-border mt-2"
                    title="Use AI to suggest unit from product name"
                  >
                    {suggestMutation.isPending ? (
                      <span className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin block" />
                    ) : (
                      <Sparkles className="w-5 h-5 text-accent" />
                    )}
                    <span className="ml-2 text-sm">Suggest unit</span>
                  </Button>
                }
              />

              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Variant attributes
                  <span className="text-xs font-normal ml-2">
                    What makes this SKU unique within its product family
                  </span>
                </p>
                <VariantAttrsEditor
                  attrs={form.variant_attrs}
                  onChange={(attrs) => setForm((f) => ({ ...f, variant_attrs: attrs }))}
                />
              </div>
            </CollapsibleContent>
          </Collapsible>

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="flex-1 btn-secondary h-12"
              data-testid="product-cancel-btn"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={saving}
              className="flex-1 btn-primary h-12"
              data-testid="product-save-btn"
            >
              {saving
                ? "Saving..."
                : editingProduct
                  ? "Update Product"
                  : isVariantMode
                    ? "Create Variant"
                    : "Create Product"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
