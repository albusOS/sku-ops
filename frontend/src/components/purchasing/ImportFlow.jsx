import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Upload, FileImage, FileText, XCircle, Sparkles, ArrowLeft } from "lucide-react";
import api, { getErrorMessage } from "@/lib/api-client";
import { ReviewFlow } from "./ReviewFlow";

const spring = { type: "spring", stiffness: 300, damping: 34 };
const fadeUp = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: spring },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
};

const TRACKED_FIELDS = ["suggested_department", "base_unit", "sell_uom", "pack_qty", "name"];

function detectCorrections(originalItems, finalPayload) {
  const corrections = [];
  for (const final of finalPayload) {
    const original = originalItems.find((o) => o.id === final.id);
    if (!original) continue;
    for (const field of TRACKED_FIELDS) {
      const orig = String(original[field] ?? "");
      const curr = String(final[field] ?? "");
      if (orig && curr && orig !== curr) {
        corrections.push({
          item_name: original.name || final.name || "",
          field,
          original_value: orig,
          corrected_value: curr,
        });
      }
    }
    if (original.sku_id && !final.sku_id) {
      corrections.push({
        item_name: original.name || "",
        field: "sku_match",
        original_value: original.sku_id,
        corrected_value: null,
      });
    }
  }
  return corrections;
}

export function ImportFlow({ onComplete, onCancel }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const [extractedData, setExtractedData] = useState(null);
  const [editedProducts, setEditedProducts] = useState([]);
  const [vendorName, setVendorName] = useState("");
  const [createVendorIfMissing, setCreateVendorIfMissing] = useState(true);

  const setPreviewSafe = (url) => {
    setPreview((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return url;
    });
  };

  const isImageOrPdf = (f) => {
    if (!f) return false;
    const t = f.type?.toLowerCase() || "";
    const n = (f.name || "").toLowerCase();
    return t.startsWith("image/") || t === "application/pdf" || n.endsWith(".pdf");
  };

  const processFile = useCallback((f) => {
    if (!f) return;
    if (!isImageOrPdf(f)) {
      toast.error("Please select an image (JPG, PNG, WEBP) or PDF");
      return;
    }
    setFile(f);
    setPreviewSafe(f.type?.startsWith("image/") ? URL.createObjectURL(f) : null);
    setExtractedData(null);
    setEditedProducts([]);
  }, []);

  const handleFileChange = (e) => processFile(e.target.files?.[0]);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragActive(false);
      processFile(e.dataTransfer.files?.[0]);
    },
    [processFile],
  );

  const extractReceipt = async (useAi = false) => {
    if (!file) {
      toast.error("Please select a document");
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
      toast.success("Items found — review them below");
    } catch (error) {
      if (error.response?.status === 503) {
        toast.error("Smart reading is not set up yet — try basic text extraction instead");
      } else {
        toast.error(error.response?.data?.detail || "Failed to extract document");
      }
    } finally {
      setExtracting(false);
    }
  };

  const handleConfirm = async (payload) => {
    const vName = (vendorName || "").trim();
    if (!vName) {
      toast.error("Vendor name is required");
      return;
    }
    setImporting(true);
    try {
      await api.purchaseOrders.create({
        vendor_name: vName,
        create_vendor_if_missing: createVendorIfMissing,
        category_id: null,
        document_date: extractedData?.document_date || null,
        total: extractedData?.total || null,
        products: payload,
      });

      const corrections = detectCorrections(editedProducts, payload);
      if (corrections.length > 0) {
        api.memory.saveCorrections({ corrections, vendor_name: vName }).catch(() => {});
      }

      toast.success(`Purchase order saved with ${payload.length} item(s)`);
      onComplete?.();
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
  };

  const inReview = !!extractedData;

  if (inReview) {
    return (
      <ReviewFlow
        items={editedProducts}
        mode="import"
        vendorName={vendorName}
        onVendorChange={setVendorName}
        createVendor={createVendorIfMissing}
        onCreateVendorChange={setCreateVendorIfMissing}
        onConfirm={handleConfirm}
        onBack={clearAll}
        submitting={importing}
        confirmLabel="Save Order"
      />
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h2 className="text-base font-semibold">Add Purchase Order</h2>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-5 space-y-5">
        <AnimatePresence mode="wait">
          {!file ? (
            <motion.div key="upload" {...fadeUp}>
              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={() => setDragActive(false)}
                onClick={() => document.getElementById("import-file-input").click()}
                className={`border border-dashed rounded-xl p-12 text-center transition-all cursor-pointer group ${
                  dragActive
                    ? "border-accent bg-accent/8 scale-[1.01]"
                    : "border-border/60 hover:border-accent/40 hover:bg-accent/5"
                }`}
              >
                <motion.div
                  animate={dragActive ? { scale: 1.08 } : { scale: 1 }}
                  transition={spring}
                  className="w-14 h-14 rounded-xl bg-gradient-to-br from-accent-gradient-from/20 to-accent-gradient-to/20 flex items-center justify-center mx-auto mb-4 border border-accent/20"
                >
                  <Upload className="w-7 h-7 text-accent" />
                </motion.div>
                <p className="text-muted-foreground font-medium">
                  Upload a vendor bill, receipt, or packing slip
                </p>
                <p className="text-muted-foreground text-sm mt-2">
                  Drop a file here, or tap to choose one
                </p>
                <p className="text-muted-foreground/60 text-xs mt-1">
                  Supports JPG, PNG, WEBP, and PDF
                </p>
                <input
                  id="import-file-input"
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>

              {/* Steps */}
              <div className="space-y-4 pt-6">
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                  How it works
                </p>
                <div className="space-y-3 text-sm text-muted-foreground">
                  {[
                    "Upload a vendor bill, receipt, or packing slip from any supplier",
                    "We'll read the document and pull out items, quantities, and prices",
                    "Review the details, make any corrections, and save",
                  ].map((text, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className="w-6 h-6 bg-accent/10 text-accent rounded-lg flex items-center justify-center text-xs font-bold shrink-0 border border-accent/20">
                        {i + 1}
                      </span>
                      <p>{text}</p>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          ) : extracting ? (
            <motion.div
              key="extracting"
              {...fadeUp}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <div className="relative">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="w-14 h-14 rounded-xl bg-gradient-to-br from-accent-gradient-from/20 to-accent-gradient-to/20 flex items-center justify-center border border-accent/20"
                >
                  <Sparkles className="w-7 h-7 text-accent" />
                </motion.div>
              </div>
              <p className="text-sm font-medium mt-5">Reading your document</p>
              <p className="text-xs text-muted-foreground mt-1">
                Extracting items, quantities, and prices…
              </p>
            </motion.div>
          ) : (
            <motion.div key="preview" {...fadeUp} className="space-y-4">
              {/* File preview */}
              <div className="relative rounded-xl overflow-hidden border border-border/60 shadow-sm">
                {preview ? (
                  <img
                    src={preview}
                    alt="Document preview"
                    className="w-full max-h-[280px] object-contain bg-muted/30"
                  />
                ) : (
                  <div className="w-full h-32 bg-muted/30 flex flex-col items-center justify-center gap-2">
                    <FileText className="w-10 h-10 text-muted-foreground" />
                    <span className="text-muted-foreground font-medium text-sm">{file.name}</span>
                    <span className="text-muted-foreground text-xs">PDF document</span>
                  </div>
                )}
                <button
                  onClick={clearAll}
                  className="absolute top-2 right-2 p-1.5 bg-card/90 backdrop-blur-sm text-muted-foreground rounded-lg hover:bg-destructive/10 hover:text-destructive border border-border shadow-sm transition-colors"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </div>

              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {preview ? <FileImage className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                <span className="truncate">{file.name}</span>
              </div>

              <div className="space-y-2">
                <Button
                  onClick={() => extractReceipt(true)}
                  disabled={extracting}
                  className="btn-primary h-11 w-full"
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Read Document
                </Button>
                <button
                  type="button"
                  onClick={() => extractReceipt(false)}
                  disabled={extracting}
                  className="w-full text-center text-xs text-muted-foreground hover:text-foreground transition-colors py-1 disabled:opacity-50"
                >
                  Use basic text extraction instead
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
