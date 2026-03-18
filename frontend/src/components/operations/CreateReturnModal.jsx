import { useState, useEffect, useMemo } from "react";
import { toast } from "sonner";
import { Loader2, Search, RotateCcw, Minus, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useWithdrawals, useWithdrawal } from "@/hooks/useWithdrawals";
import { useCreateReturn } from "@/hooks/useReturns";
import { getErrorMessage } from "@/lib/api-client";

const REASON_OPTIONS = [
  { value: "wrong_item", label: "Wrong Item" },
  { value: "defective", label: "Defective" },
  { value: "overorder", label: "Over-ordered" },
  { value: "job_cancelled", label: "Job Cancelled" },
  { value: "other", label: "Other" },
];

export function CreateReturnModal({ open, onOpenChange, prefillWithdrawalId }) {
  const [step, setStep] = useState(prefillWithdrawalId ? 1 : 0);
  const [withdrawalId, setWithdrawalId] = useState(prefillWithdrawalId || "");
  const [wdSearch, setWdSearch] = useState("");
  const [reason, setReason] = useState("other");
  const [notes, setNotes] = useState("");
  const [returnItems, setReturnItems] = useState([]);

  const { data: withdrawals = [] } = useWithdrawals();
  const { data: selectedWd } = useWithdrawal(withdrawalId || null);
  const createReturn = useCreateReturn();

  useEffect(() => {
    if (open) {
      setStep(prefillWithdrawalId ? 1 : 0);
      setWithdrawalId(prefillWithdrawalId || "");
      setWdSearch("");
      setReason("other");
      setNotes("");
      setReturnItems([]);
    }
  }, [open, prefillWithdrawalId]);

  useEffect(() => {
    if (selectedWd?.items && step === 1 && returnItems.length === 0) {
      setReturnItems(
        selectedWd.items.map((item) => ({
          sku_id: item.sku_id,
          sku: item.sku || "",
          name: item.product_name || item.description || item.name || "",
          quantity: 0,
          max_quantity: item.quantity,
          unit_price: item.unit_price ?? 0,
          cost: item.cost ?? 0,
          unit: item.unit || "each",
          reason: "other",
        })),
      );
    }
  }, [selectedWd, step, returnItems.length]);

  const filteredWithdrawals = useMemo(() => {
    if (!wdSearch) return withdrawals.slice(0, 20);
    const q = wdSearch.toLowerCase();
    return withdrawals
      .filter(
        (w) =>
          w.contractor_name?.toLowerCase().includes(q) ||
          w.job_id?.toLowerCase().includes(q) ||
          w.billing_entity?.toLowerCase().includes(q) ||
          w.id?.toLowerCase().includes(q),
      )
      .slice(0, 20);
  }, [withdrawals, wdSearch]);

  const updateItemQty = (idx, delta) => {
    setReturnItems((prev) =>
      prev.map((item, i) => {
        if (i !== idx) return item;
        const next = Math.max(0, Math.min(item.max_quantity, item.quantity + delta));
        return { ...item, quantity: next };
      }),
    );
  };

  const setItemQty = (idx, value) => {
    setReturnItems((prev) =>
      prev.map((item, i) => {
        if (i !== idx) return item;
        const num = parseFloat(value) || 0;
        return { ...item, quantity: Math.max(0, Math.min(item.max_quantity, num)) };
      }),
    );
  };

  const setItemReason = (idx, value) => {
    setReturnItems((prev) =>
      prev.map((item, i) => (i !== idx ? item : { ...item, reason: value })),
    );
  };

  const itemsToReturn = returnItems.filter((i) => i.quantity > 0);
  const refundTotal = itemsToReturn.reduce((s, i) => s + i.quantity * i.unit_price, 0);

  const handleSelectWithdrawal = (id) => {
    setWithdrawalId(id);
    setReturnItems([]);
    setStep(1);
  };

  const handleSubmit = async () => {
    if (itemsToReturn.length === 0) {
      toast.error("Select at least one item to return");
      return;
    }
    try {
      await createReturn.mutateAsync({
        withdrawal_id: withdrawalId,
        items: itemsToReturn.map((i) => ({
          sku_id: i.sku_id,
          sku: i.sku,
          name: i.name,
          quantity: i.quantity,
          unit_price: i.unit_price,
          cost: i.cost,
          unit: i.unit,
          reason: i.reason,
        })),
        reason,
        notes: notes || undefined,
      });
      toast.success("Return processed — inventory restocked");
      onOpenChange(false);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="w-5 h-5" />
            Process Return
          </DialogTitle>
          <DialogDescription>
            {step === 0
              ? "Select the original sale to return items from."
              : "Choose items and quantities to return."}
          </DialogDescription>
        </DialogHeader>

        {step === 0 && (
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by contractor, job, entity, or ID…"
                value={wdSearch}
                onChange={(e) => setWdSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="border border-border rounded-lg max-h-64 overflow-y-auto divide-y divide-border">
              {filteredWithdrawals.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-6">No sales found</p>
              )}
              {filteredWithdrawals.map((wd) => (
                <button
                  key={wd.id}
                  type="button"
                  onClick={() => handleSelectWithdrawal(wd.id)}
                  className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">{wd.contractor_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(wd.created_at).toLocaleDateString()}
                      {wd.job_id && ` · ${wd.job_id}`}
                      {wd.billing_entity && ` · ${wd.billing_entity}`}
                    </p>
                  </div>
                  <span className="font-mono text-sm font-semibold">
                    ${(wd.total || 0).toFixed(2)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            {selectedWd && (
              <div className="bg-muted/50 rounded-lg px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{selectedWd.contractor_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(selectedWd.created_at).toLocaleDateString()}
                    {selectedWd.job_id && ` · ${selectedWd.job_id}`}
                  </p>
                </div>
                {!prefillWithdrawalId && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setStep(0);
                      setReturnItems([]);
                    }}
                  >
                    Change
                  </Button>
                )}
              </div>
            )}

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Items to Return
              </Label>
              <div className="mt-2 border border-border rounded-lg divide-y divide-border">
                {returnItems.map((item, idx) => (
                  <div key={idx} className="px-4 py-3 flex items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{item.name}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">
                        {item.sku} · max {item.max_quantity} {item.unit}
                      </p>
                    </div>
                    <Select value={item.reason} onValueChange={(v) => setItemReason(idx, v)}>
                      <SelectTrigger className="w-32 h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {REASON_OPTIONS.map((o) => (
                          <SelectItem key={o.value} value={o.value}>
                            {o.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => updateItemQty(idx, -1)}
                        className="w-7 h-7 rounded-md border border-border flex items-center justify-center hover:bg-muted transition-colors"
                      >
                        <Minus className="w-3 h-3" />
                      </button>
                      <Input
                        type="number"
                        min={0}
                        max={item.max_quantity}
                        value={item.quantity}
                        onChange={(e) => setItemQty(idx, e.target.value)}
                        className="w-16 h-7 text-center text-sm font-mono px-1"
                      />
                      <button
                        type="button"
                        onClick={() => updateItemQty(idx, 1)}
                        className="w-7 h-7 rounded-md border border-border flex items-center justify-center hover:bg-muted transition-colors"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                    <span className="w-20 text-right font-mono text-sm text-destructive font-semibold">
                      {item.quantity > 0
                        ? `-$${(item.quantity * item.unit_price).toFixed(2)}`
                        : "—"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="return-reason">Overall Reason</Label>
                <Select value={reason} onValueChange={setReason}>
                  <SelectTrigger id="return-reason" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {REASON_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Refund Total</Label>
                <p className="mt-2 text-lg font-bold font-mono text-destructive">
                  ${refundTotal.toFixed(2)}
                </p>
              </div>
            </div>

            <div>
              <Label htmlFor="return-notes">Notes (optional)</Label>
              <Textarea
                id="return-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional details about this return…"
                className="mt-1"
                rows={2}
              />
            </div>
          </div>
        )}

        {step === 1 && (
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={itemsToReturn.length === 0 || createReturn.isPending}
              className="bg-destructive hover:bg-destructive/90 text-destructive-foreground gap-2"
            >
              {createReturn.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RotateCcw className="w-4 h-4" />
              )}
              {createReturn.isPending
                ? "Processing…"
                : `Return ${itemsToReturn.length} item${itemsToReturn.length !== 1 ? "s" : ""}`}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
