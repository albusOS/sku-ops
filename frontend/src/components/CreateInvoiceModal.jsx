import { useState, useEffect } from "react";
import axios from "axios";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { toast } from "sonner";
import { API } from "@/lib/api";

export function CreateInvoiceModal({ open, onOpenChange, onCreated, preselectedIds = [] }) {
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [entityFilter, setEntityFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState(new Set(preselectedIds));

  useEffect(() => {
    if (open) {
      setSelectedIds(new Set(preselectedIds));
      fetchUnpaid();
    }
  }, [open, preselectedIds]);

  const fetchUnpaid = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ payment_status: "unpaid" });
      const res = await axios.get(`${API}/withdrawals?${params}`);
      setWithdrawals(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const unpaidByEntity = withdrawals.reduce((acc, w) => {
    const be = w.billing_entity || "(No entity)";
    if (!acc[be]) acc[be] = [];
    acc[be].push(w);
    return acc;
  }, {});

  const entities = Object.keys(unpaidByEntity).sort();
  const filtered = entityFilter ? (unpaidByEntity[entityFilter] || []) : withdrawals;

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllInFiltered = () => {
    const ids = filtered.filter((w) => !w.invoice_id).map((w) => w.id);
    setSelectedIds((prev) => new Set([...prev, ...ids]));
  };

  const handleCreate = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    setSaving(true);
    try {
      const res = await axios.post(`${API}/invoices`, { withdrawal_ids: ids });
      toast.success("Invoice created");
      onCreated?.(res.data);
      onOpenChange(false);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Failed to create invoice";
      toast.error(typeof msg === "string" ? msg : "Failed to create invoice");
    } finally {
      setSaving(false);
    }
  };

  const eligible = filtered.filter((w) => !w.invoice_id);
  const selectedEligible = eligible.filter((w) => selectedIds.has(w.id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl rounded-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Create Invoice</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-slate-600">
          Select unpaid withdrawals. All must share the same billing entity.
        </p>

        <div className="flex items-center gap-3">
          <label className="text-sm font-medium">Billing Entity</label>
          <Select value={entityFilter || "all"} onValueChange={(v) => setEntityFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="All entities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All entities</SelectItem>
              {entities.map((e) => (
                <SelectItem key={e} value={e}>
                  {e}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={selectAllInFiltered}>
            Select all in list
          </Button>
        </div>

        <div className="flex-1 overflow-auto border border-slate-200 rounded-lg min-h-[200px]">
          {loading ? (
            <div className="p-6 text-center text-slate-500">Loading…</div>
          ) : eligible.length === 0 ? (
            <div className="p-6 text-center text-slate-500">
              No unpaid withdrawals
              {entityFilter ? ` for ${entityFilter}` : ""}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="w-10 px-3 py-2 text-left"></th>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Job ID</th>
                  <th className="px-3 py-2 text-left">Entity</th>
                  <th className="px-3 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {eligible.map((w) => (
                  <tr key={w.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(w.id)}
                        onChange={() => toggleSelect(w.id)}
                        className="w-4 h-4 rounded border-slate-300"
                      />
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {new Date(w.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2 font-mono">{w.job_id}</td>
                    <td className="px-3 py-2">{w.billing_entity || "—"}</td>
                    <td className="px-3 py-2 text-right font-mono">${w.total?.toFixed(2) || "0.00"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="flex justify-between items-center pt-4 border-t">
          <span className="text-sm text-slate-600">
            {selectedIds.size} withdrawal(s) selected
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={selectedIds.size === 0 || saving}
            >
              {saving ? "Creating…" : "Create Invoice"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
