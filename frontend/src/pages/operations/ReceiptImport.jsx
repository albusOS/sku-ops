import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/PageHeader";
import { Panel, SectionHead } from "@/components/Panel";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Upload,
  FileImage,
  ClipboardList,
  XCircle,
  X,
  Loader2,
  Trash2,
  Sparkles,
  FileText,
} from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import api from "@/lib/api-client";
import { getErrorMessage } from "@/lib/api-client";
import { useDepartments } from "@/hooks/useDepartments";
import { useProductMatch } from "@/hooks/useProductMatch";
import { ProductMatchPicker } from "@/components/ProductMatchPicker";
import { ProductFields } from "@/components/ProductFields";

const PANEL_SPRING = { type: "spring", stiffness: 300, damping: 36 };

const ReceiptImport = () => {
  const navigate = useNavigate();
  const { data: departments = [] } = useDepartments();
  const [selectedDept, setSelectedDept] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [createVendorIfMissing, setCreateVendorIfMissing] = useState(true);
  const [vendorName, setVendorName] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [editedProducts, setEditedProducts] = useState([]);
  const {
    matches: productMatches,
    autoMatch,
    searchMatch,
    confirmMatch,
    clearMatch,
    reset: resetMatches,
  } = useProductMatch();

  const setPreviewSafe = (url) => {
    setPreview((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return url;
    });
  };

  const isImageOrPdf = (file) => {
    if (!file) return false;
    const t = file.type?.toLowerCase() || "";
    const n = (file.name || "").toLowerCase();
    return t.startsWith("image/") || t === "application/pdf" || n.endsWith(".pdf");
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!isImageOrPdf(selectedFile)) {
        toast.error("Please select an image (JPG, PNG, WEBP) or PDF");
        return;
      }
      setFile(selectedFile);
      setPreviewSafe(
        selectedFile.type?.startsWith("image/") ? URL.createObjectURL(selectedFile) : null,
      );
      setExtractedData(null);
      setEditedProducts([]);
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      if (!isImageOrPdf(droppedFile)) {
        toast.error("Please select an image (JPG, PNG, WEBP) or PDF");
        return;
      }
      setFile(droppedFile);
      setPreviewSafe(
        droppedFile.type?.startsWith("image/") ? URL.createObjectURL(droppedFile) : null,
      );
      setExtractedData(null);
      setEditedProducts([]);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  const extractReceipt = async (useAi = false) => {
    if (!file) {
      toast.error("Please select a document (image or PDF)");
      return;
    }

    setExtracting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.documents.parse(formData, useAi);

      setExtractedData(response);
      setVendorName(response.vendor_name || "");
      const mapped = (response.products || []).map((p, idx) => ({
        ...p,
        id: idx,
        selected: true,
        quantity: p.quantity ?? 1,
        ordered_qty: p.ordered_qty ?? p.quantity ?? 1,
        delivered_qty: p.delivered_qty ?? p.quantity ?? 1,
        base_unit: p.base_unit || "each",
        pack_qty: p.pack_qty ?? 1,
        min_stock: 5,
        matched_product: null,
      }));
      setEditedProducts(mapped);
      toast.success("Document extracted successfully!");
      autoMatch(mapped);
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to extract document";
      if (error.response?.status === 503) {
        toast.error(
          "AI not configured — add ANTHROPIC_API_KEY to backend/.env, or use free OCR instead",
        );
      } else {
        toast.error(detail);
      }
    } finally {
      setExtracting(false);
    }
  };

  const updateProduct = (id, field, value) => {
    setEditedProducts(editedProducts.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  const toggleProduct = (id) => {
    setEditedProducts(
      editedProducts.map((p) => (p.id === id ? { ...p, selected: !p.selected } : p)),
    );
  };

  const removeProduct = (id) => {
    setEditedProducts(editedProducts.filter((p) => p.id !== id));
  };

  const saveAsPurchaseOrder = async () => {
    const vName = (vendorName || extractedData?.vendor_name || "").trim();
    if (!vName) {
      toast.error("Vendor name is required");
      return;
    }

    const productsToSave = editedProducts
      .filter((p) => p.selected)
      .map((p) => ({
        name: p.name,
        quantity: parseFloat(p.quantity) || 1,
        ordered_qty:
          p.ordered_qty != null ? parseFloat(p.ordered_qty) : parseFloat(p.quantity) || 1,
        delivered_qty:
          p.delivered_qty != null ? parseFloat(p.delivered_qty) : parseFloat(p.quantity) || 1,
        price: parseFloat(p.price) || 0,
        cost: p.cost != null ? parseFloat(p.cost) : undefined,
        original_sku: p.original_sku,
        base_unit: p.base_unit || undefined,
        sell_uom: p.sell_uom || p.base_unit || undefined,
        pack_qty: p.pack_qty != null ? parseInt(p.pack_qty) : undefined,
        suggested_department: p.suggested_department || undefined,
        min_stock: p.min_stock != null ? parseInt(p.min_stock) : 5,
        product_id: p.matched_product?.id || undefined,
        _ai_parsed: p._ai_parsed || false,
        selected: true,
      }));

    if (productsToSave.length === 0) {
      toast.error("No products selected");
      return;
    }

    setImporting(true);
    try {
      await api.purchaseOrders.create({
        vendor_name: vName,
        create_vendor_if_missing: createVendorIfMissing,
        category_id: selectedDept || null,
        document_date: extractedData?.document_date || null,
        total: extractedData?.total || null,
        products: productsToSave,
      });

      toast.success(`Purchase order saved — ${productsToSave.length} item(s) pending receipt`);
      setFile(null);
      setPreviewSafe(null);
      setExtractedData(null);
      setEditedProducts([]);
      setVendorName("");
      navigate("/purchase-orders");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setImporting(false);
    }
  };

  const clearAll = () => {
    setFile(null);
    setPreviewSafe(null);
    setExtractedData(null);
    setEditedProducts([]);
    setVendorName("");
    resetMatches();
  };

  const handleConfirmMatch = (itemId, product) => {
    setEditedProducts((prev) =>
      prev.map((p) => (p.id === itemId ? { ...p, matched_product: product } : p)),
    );
    confirmMatch(itemId, product);
  };

  const handleClearMatch = (itemId) => {
    setEditedProducts((prev) =>
      prev.map((p) => (p.id === itemId ? { ...p, matched_product: null } : p)),
    );
    clearMatch(itemId);
  };

  const panelOpen = !!extractedData;
  const selectedCount = editedProducts.filter((p) => p.selected).length;
  const selectedTotal = editedProducts
    .filter((p) => p.selected)
    .reduce((sum, p) => sum + (parseFloat(p.price) || 0) * (p.delivered_qty ?? p.quantity ?? 1), 0);

  return (
    <div className="h-full flex flex-col" data-testid="receipt-import-page">
      {/* Page header */}
      <div className="px-8 pt-8 pb-0 shrink-0">
        <PageHeader
          title="Receive / Import"
          subtitle="Upload a delivery receipt or vendor invoice to extract products and create a purchase order"
        />
      </div>

      {/* Content area — main + side panel split */}
      <div className="flex-1 flex min-h-0 mt-3">
        {/* Upload section (main area) */}
        <motion.div
          layout
          animate={{ width: panelOpen ? "58%" : "100%" }}
          transition={PANEL_SPRING}
          className="h-full overflow-auto px-8 pb-8 shrink-0"
        >
          <Panel data-testid="upload-section">
            <SectionHead
              title="Upload document"
              action={
                <span className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/20 text-accent flex items-center justify-center text-xs font-bold">
                  1
                </span>
              }
            />

            {!file ? (
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="border border-dashed border-border/60 rounded-xl p-12 text-center hover:border-accent/40 hover:bg-accent/5 transition-all cursor-pointer group"
                onClick={() => document.getElementById("receipt-input").click()}
                data-testid="upload-dropzone"
              >
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-accent-gradient-from/20 to-accent-gradient-to/20 flex items-center justify-center mx-auto mb-4 group-hover:scale-105 transition-transform border border-accent/20">
                  <Upload className="w-7 h-7 text-accent" />
                </div>
                <p className="text-muted-foreground font-medium">
                  Drop document here or click to browse
                </p>
                <p className="text-muted-foreground text-sm mt-2">Supports JPG, PNG, WEBP, PDF</p>
                <input
                  id="receipt-input"
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={handleFileChange}
                  className="hidden"
                  data-testid="receipt-file-input"
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="relative rounded-xl overflow-hidden border border-border/60 shadow-sm">
                  {preview ? (
                    <img
                      src={preview}
                      alt="Document preview"
                      className="w-full max-h-[400px] object-contain bg-muted/30"
                      data-testid="receipt-preview"
                    />
                  ) : (
                    <div className="w-full h-48 bg-muted/30 flex flex-col items-center justify-center gap-2">
                      <FileText className="w-12 h-12 text-muted-foreground" />
                      <span className="text-muted-foreground font-medium">{file.name}</span>
                      <span className="text-muted-foreground text-sm">PDF document</span>
                    </div>
                  )}
                  <button
                    onClick={clearAll}
                    className="absolute top-3 right-3 p-2 bg-card/95 backdrop-blur-sm text-muted-foreground rounded-xl hover:bg-destructive/10 hover:text-destructive border border-border shadow-sm transition-colors"
                    data-testid="clear-receipt-btn"
                  >
                    <XCircle className="w-5 h-5" />
                  </button>
                </div>

                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  {preview ? <FileImage className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                  <span>{file?.name}</span>
                </div>

                <div className="grid grid-cols-2 gap-2" data-testid="extract-btn">
                  <Button
                    onClick={() => extractReceipt(true)}
                    disabled={extracting}
                    className="btn-primary h-11"
                  >
                    {extracting ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Sparkles className="w-4 h-4 mr-2" />
                    )}
                    Extract with AI
                  </Button>
                  <Button
                    onClick={() => extractReceipt(false)}
                    disabled={extracting}
                    variant="outline"
                    className="h-11 text-muted-foreground"
                  >
                    {extracting ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <FileText className="w-4 h-4 mr-2" />
                    )}
                    Free OCR
                  </Button>
                </div>
              </div>
            )}
          </Panel>

          {/* How It Works */}
          {!panelOpen && (
            <Panel className="mt-6">
              <SectionHead
                title="How it works"
                action={<Sparkles className="w-4 h-4 text-accent" />}
              />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-muted-foreground">
                {[
                  {
                    num: "1",
                    text: "Upload a receipt, invoice, or PDF from any hardware store (Home Depot, Lowes, etc.)",
                  },
                  {
                    num: "2",
                    text: (
                      <>
                        <strong className="text-foreground">AI extracts</strong> vendor, items, UOM,
                        costs, and quantities
                      </>
                    ),
                  },
                  {
                    num: "3",
                    text: "Products get new SKUs in your system and are added to inventory",
                  },
                ].map(({ num, text }) => (
                  <div key={num} className="flex items-start gap-4">
                    <span className="w-9 h-9 bg-accent/10 text-accent rounded-xl flex items-center justify-center font-semibold shrink-0 border border-accent/20">
                      {num}
                    </span>
                    <p>{text}</p>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </motion.div>

        {/* Review & Import panel */}
        <AnimatePresence>
          {panelOpen && (
            <motion.div
              key="review-panel"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: "42%", opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={PANEL_SPRING}
              className="h-full shrink-0 overflow-hidden"
            >
              <div
                className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden shadow-xl"
                data-testid="extracted-section"
              >
                {/* Panel header */}
                <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center shrink-0">
                        <ClipboardList className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div className="min-w-0">
                        <h2 className="text-base font-semibold leading-tight">Review & import</h2>
                        <p className="text-muted-foreground text-xs mt-0.5">
                          {editedProducts.length} item{editedProducts.length !== 1 ? "s" : ""}{" "}
                          extracted
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={clearAll}
                      className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
                      aria-label="Close panel"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Quick stats strip */}
                  <div className="grid grid-cols-3 gap-2 mt-4">
                    {[
                      { label: "Selected", value: selectedCount },
                      { label: "Items", value: editedProducts.length },
                      {
                        label: "Total",
                        value: selectedCount > 0 ? `$${selectedTotal.toFixed(2)}` : "—",
                      },
                    ].map(({ label, value }) => (
                      <div
                        key={label}
                        className="rounded-lg px-3 py-2 text-center bg-muted/50 border border-border/40"
                      >
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">
                          {label}
                        </p>
                        <p className="font-mono font-semibold text-sm">{value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Panel content */}
                <div className="flex-1 overflow-auto px-5 py-4 space-y-4">
                  <div>
                    <Label className="text-muted-foreground font-medium text-sm">Vendor *</Label>
                    <Input
                      value={vendorName}
                      onChange={(e) => setVendorName(e.target.value)}
                      className="input-field mt-2"
                      placeholder="Vendor / store name"
                      data-testid="vendor-name-input"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="create-vendor"
                      checked={createVendorIfMissing}
                      onCheckedChange={(c) => setCreateVendorIfMissing(c === true)}
                    />
                    <Label
                      htmlFor="create-vendor"
                      className="text-sm text-muted-foreground cursor-pointer"
                    >
                      Create vendor if missing
                    </Label>
                  </div>

                  <div>
                    <Label className="text-muted-foreground font-medium text-sm">
                      Category override (optional)
                    </Label>
                    <Select
                      value={selectedDept || "none"}
                      onValueChange={(v) => setSelectedDept(v === "none" ? "" : v)}
                    >
                      <SelectTrigger className="input-field mt-2" data-testid="import-dept-select">
                        <SelectValue placeholder="Use suggested per product" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Use suggested per product</SelectItem>
                        {departments.map((dept) => (
                          <SelectItem key={dept.id} value={dept.id}>
                            {dept.name} ({dept.code})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-3" data-testid="extracted-products-list">
                    <AnimatePresence initial={false}>
                      {editedProducts.map((product) => {
                        const matchState = productMatches[product.id] || {};
                        const matched = matchState.matched || product.matched_product;

                        return (
                          <motion.div
                            key={product.id}
                            layout
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ type: "spring", stiffness: 340, damping: 38 }}
                            className={`p-4 rounded-xl border transition-all ${
                              product.selected
                                ? "border-accent/30 bg-accent/5 shadow-sm"
                                : "border-border bg-muted/50 opacity-60"
                            }`}
                            data-testid={`extracted-product-${product.id}`}
                          >
                            <div className="flex items-start gap-3">
                              <button
                                onClick={() => toggleProduct(product.id)}
                                className={`mt-1 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-colors ${
                                  product.selected
                                    ? "bg-accent border-accent text-white"
                                    : "border-border"
                                }`}
                                data-testid={`toggle-product-${product.id}`}
                              >
                                {product.selected && (
                                  <svg
                                    className="w-3 h-3 text-white"
                                    fill="currentColor"
                                    viewBox="0 0 20 20"
                                  >
                                    <path
                                      fillRule="evenodd"
                                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                )}
                              </button>

                              <div className="flex-1 min-w-0 space-y-2">
                                <ProductMatchPicker
                                  matched={matched}
                                  options={matchState.options || []}
                                  searching={matchState.searching || false}
                                  onSearch={(q) => searchMatch(product.id, q)}
                                  onConfirm={(p) => handleConfirmMatch(product.id, p)}
                                  onClear={() => handleClearMatch(product.id)}
                                />

                                {matched ? (
                                  <div className="space-y-2">
                                    <div className="grid grid-cols-2 gap-2">
                                      <div>
                                        <Label className="text-xs text-muted-foreground">
                                          Delivered qty
                                        </Label>
                                        <Input
                                          type="number"
                                          step="any"
                                          value={product.delivered_qty ?? product.quantity ?? 1}
                                          onChange={(e) =>
                                            updateProduct(
                                              product.id,
                                              "delivered_qty",
                                              e.target.value,
                                            )
                                          }
                                          className="input-field h-9 text-sm"
                                        />
                                      </div>
                                      <div>
                                        <Label className="text-xs text-muted-foreground">
                                          Cost
                                        </Label>
                                        <Input
                                          type="number"
                                          step="0.01"
                                          value={product.cost ?? ""}
                                          onChange={(e) =>
                                            updateProduct(
                                              product.id,
                                              "cost",
                                              e.target.value ? parseFloat(e.target.value) : null,
                                            )
                                          }
                                          className="input-field h-9 text-sm"
                                        />
                                      </div>
                                    </div>
                                    {product.original_sku && (
                                      <p className="text-xs text-muted-foreground font-mono">
                                        Original: {product.original_sku}
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <ProductFields
                                    compact
                                    fields={{
                                      name: product.name || "",
                                      price: product.price ?? "",
                                      cost: product.cost ?? "",
                                      base_unit: product.base_unit || "each",
                                      sell_uom: product.sell_uom || "each",
                                      pack_qty: product.pack_qty ?? 1,
                                      barcode: product.barcode || "",
                                      category_id: product.suggested_department || "",
                                      quantity: product.delivered_qty ?? product.quantity ?? 1,
                                    }}
                                    onChange={(field, value) => {
                                      const mapped =
                                        field === "category_id"
                                          ? "suggested_department"
                                          : field === "quantity"
                                            ? "delivered_qty"
                                            : field;
                                      updateProduct(product.id, mapped, value);
                                    }}
                                    departments={departments}
                                    hiddenFields={[
                                      "description",
                                      "vendor_id",
                                      "min_stock",
                                      "sell_uom",
                                      "pack_qty",
                                    ]}
                                  />
                                )}
                              </div>

                              <button
                                onClick={() => removeProduct(product.id)}
                                className="p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors shrink-0"
                                data-testid={`remove-product-${product.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </motion.div>
                        );
                      })}
                    </AnimatePresence>
                  </div>
                </div>

                {/* Sticky footer */}
                <div className="px-5 py-4 border-t border-border bg-muted/80 shrink-0 space-y-3">
                  <p className="text-sm text-muted-foreground">
                    <strong>{selectedCount}</strong> of {editedProducts.length} products selected
                  </p>
                  <Button
                    onClick={saveAsPurchaseOrder}
                    disabled={importing || !(vendorName || "").trim()}
                    className="w-full btn-primary h-11"
                    data-testid="import-products-btn"
                  >
                    {importing ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        Saving…
                      </>
                    ) : (
                      <>
                        <ClipboardList className="w-5 h-5 mr-2" />
                        Save as Purchase Order
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ReceiptImport;
