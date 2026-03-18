import { useState, useMemo } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ADJUST_REASONS } from "@/lib/constants";
import { getErrorMessage } from "@/lib/api-client";
import { useAdjustStock } from "@/hooks/useProducts";

const MODES = [
  { key: "delta", label: "Adjust by delta" },
  { key: "counted", label: "Counted quantity" },
];

export function AdjustStockDialog({ product, open, onOpenChange }) {
  const [mode, setMode] = useState("delta");
  const [inputValue, setInputValue] = useState("");
  const [reason, setReason] = useState("correction");
  const adjustMutation = useAdjustStock();

  const unit = product?.base_unit || "each";
  const currentQty = product?.quantity ?? 0;

  const effectiveDelta = useMemo(() => {
    const v = parseFloat(inputValue);
    if (isNaN(v)) return NaN;
    return mode === "counted" ? v - currentQty : v;
  }, [inputValue, mode, currentQty]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isNaN(effectiveDelta) || effectiveDelta === 0) {
      toast.error(
        mode === "counted"
          ? "Counted quantity must differ from current stock"
          : "Enter a non-zero quantity delta",
      );
      return;
    }
    if (!product) return;

    adjustMutation.mutate(
      { id: product.id, data: { quantity_delta: effectiveDelta, reason } },
      {
        onSuccess: () => {
          toast.success("Stock adjusted");
          setInputValue("");
          setMode("delta");
          setReason("correction");
          onOpenChange(false);
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  const formatDelta = (d) => {
    const sign = d > 0 ? "+" : "";
    return `${sign}${d} ${unit}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Adjust Stock</DialogTitle>
          {product && (
            <p className="text-sm text-muted-foreground">
              {product.sku} — {product.name}
            </p>
          )}
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-4">
          <p className="text-sm text-muted-foreground">
            Current stock:{" "}
            <span className="font-medium text-foreground">
              {currentQty} {unit}
            </span>
          </p>

          <div
            className="inline-flex rounded-lg border border-border p-0.5 bg-muted"
            role="tablist"
          >
            {MODES.map((m) => (
              <button
                key={m.key}
                type="button"
                role="tab"
                aria-selected={mode === m.key}
                onClick={() => {
                  setMode(m.key);
                  setInputValue("");
                }}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  mode === m.key
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          <div>
            <Label>
              {mode === "delta"
                ? "Quantity delta (positive to add, negative to remove)"
                : "Counted quantity"}
            </Label>
            <div className="flex items-center gap-2 mt-2">
              <Input
                type="number"
                step="any"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={mode === "delta" ? "e.g. 5 or -3" : "e.g. 120"}
                className="input-workshop"
              />
              <span className="text-sm text-muted-foreground shrink-0">{unit}</span>
            </div>
            {mode === "counted" && inputValue !== "" && !isNaN(parseFloat(inputValue)) && (
              <p className="text-sm mt-1.5">
                Adjustment:{" "}
                <span
                  className={
                    effectiveDelta > 0
                      ? "font-medium text-green-600"
                      : effectiveDelta < 0
                        ? "font-medium text-red-600"
                        : "font-medium text-muted-foreground"
                  }
                >
                  {formatDelta(effectiveDelta)}
                </span>
              </p>
            )}
          </div>

          <div>
            <Label>Reason</Label>
            <Select value={reason} onValueChange={setReason}>
              <SelectTrigger className="input-workshop mt-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ADJUST_REASONS.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={adjustMutation.isPending}>
              {adjustMutation.isPending ? "Adjusting..." : "Adjust"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
