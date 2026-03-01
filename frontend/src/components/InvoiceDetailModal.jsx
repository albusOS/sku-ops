import { useState, useEffect } from "react";
import axios from "axios";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { FileText, Trash2, Plus, ExternalLink } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { API } from "@/lib/api";
import { ConfirmDialog } from "@/components/ConfirmDialog";

function StatusBadge({ status }) {
  const styles = {
    draft: "bg-slate-200 text-slate-700",
    sent: "bg-blue-100 text-blue-700",
    paid: "bg-green-100 text-green-700",
  };
  return (
    <span
      className={`px-2.5 py-1 rounded-sm text-xs font-bold uppercase ${styles[status] || "bg-slate-200"}`}
    >
      {status}
    </span>
  );
}

export function InvoiceDetailModal({ invoiceId, open, onOpenChange, onSaved, onDeleted }) {
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const [form, setForm] = useState({
    billing_entity: "",
    contact_name: "",
    contact_email: "",
    notes: "",
    tax: 0,
    status: "draft",
  });
  const [lineItems, setLineItems] = useState([]);

  useEffect(() => {
    if (open && invoiceId) {
      fetchInvoice();
    }
  }, [open, invoiceId]);

  const fetchInvoice = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/invoices/${invoiceId}`);
      setInvoice(res.data);
      setForm({
        billing_entity: res.data.billing_entity || "",
        contact_name: res.data.contact_name || "",
        contact_email: res.data.contact_email || "",
        notes: res.data.notes || "",
        tax: res.data.tax ?? 0,
        status: res.data.status || "draft",
      });
      setLineItems(res.data.line_items || []);
    } catch (err) {
      toast.error("Failed to load invoice");
    } finally {
      setLoading(false);
    }
  };

  const recalcTotals = (items, taxVal) => {
    const subtotal = items.reduce((sum, i) => sum + (i.amount ?? i.quantity * i.unit_price), 0);
    const tax = typeof taxVal === "number" ? taxVal : parseFloat(taxVal) || 0;
    return { subtotal: Math.round(subtotal * 100) / 100, total: Math.round((subtotal + tax) * 100) / 100 };
  };

  const updateLineItem = (idx, field, value) => {
    const next = [...lineItems];
    next[idx] = { ...next[idx], [field]: value };
    if (field === "quantity" || field === "unit_price") {
      const qty = parseFloat(next[idx].quantity) || 0;
      const price = parseFloat(next[idx].unit_price) || 0;
      next[idx].amount = Math.round(qty * price * 100) / 100;
    }
    setLineItems(next);
  };

  const addLineItem = () => {
    setLineItems([...lineItems, { id: crypto.randomUUID(), description: "", quantity: 1, unit_price: 0, amount: 0 }]);
  };

  const removeLineItem = (idx) => {
    setLineItems(lineItems.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const items = lineItems.map((i) => ({
        id: i.id,
        description: i.description || "",
        quantity: parseFloat(i.quantity) || 0,
        unit_price: parseFloat(i.unit_price) || 0,
        amount: (parseFloat(i.quantity) || 0) * (parseFloat(i.unit_price) || 0),
        product_id: i.product_id,
      }));
      await axios.put(`${API}/invoices/${invoiceId}`, {
        billing_entity: form.billing_entity,
        contact_name: form.contact_name,
        contact_email: form.contact_email,
        notes: form.notes,
        tax: parseFloat(form.tax) || 0,
        status: form.status,
        line_items: items,
      });
      toast.success("Invoice saved");
      setEditing(false);
      fetchInvoice();
      onSaved?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = () => {
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    try {
      await axios.delete(`${API}/invoices/${invoiceId}`);
      toast.success("Invoice deleted");
      onDeleted?.();
      onOpenChange(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete");
      throw err;
    }
  };

  const handleSyncXero = async () => {
    try {
      const res = await axios.post(`${API}/invoices/${invoiceId}/sync-xero`);
      toast.info(res.data?.message || "Xero integration coming soon");
    } catch (err) {
      toast.error("Failed");
    }
  };

  const { subtotal, total } = recalcTotals(lineItems, form.tax);
  const canEdit = invoice?.status === "draft";

  if (!invoice && !loading) return null;

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl rounded-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-slate-500" />
            <span>{invoice?.invoice_number || "Invoice"}</span>
            {invoice && <StatusBadge status={invoice.status} />}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="py-8 text-center text-slate-500">Loading…</div>
        ) : (
          <div className="flex-1 overflow-auto space-y-6">
            {/* Bill to */}
            <div>
              <Label className="text-xs uppercase text-slate-500">Bill To</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                <div>
                  <label className="text-xs text-slate-500">Billing Entity</label>
                  <Input
                    value={form.billing_entity}
                    onChange={(e) => setForm((f) => ({ ...f, billing_entity: e.target.value }))}
                    disabled={!canEdit}
                    className="mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Contact Name</label>
                  <Input
                    value={form.contact_name}
                    onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
                    disabled={!canEdit}
                    className="mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Contact Email</label>
                  <Input
                    type="email"
                    value={form.contact_email}
                    onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                    disabled={!canEdit}
                    className="mt-0.5"
                  />
                </div>
              </div>
            </div>

            {/* Line items */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <Label className="text-xs uppercase text-slate-500">Line Items</Label>
                {canEdit && (
                  <Button variant="ghost" size="sm" onClick={addLineItem}>
                    <Plus className="w-4 h-4 mr-1" />
                    Add row
                  </Button>
                )}
              </div>
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="px-3 py-2 text-left">Description</th>
                      <th className="px-3 py-2 text-right w-20">Qty</th>
                      <th className="px-3 py-2 text-right w-24">Unit $</th>
                      <th className="px-3 py-2 text-right w-24">Amount</th>
                      {canEdit && <th className="w-10"></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {lineItems.map((item, idx) => (
                      <tr key={item.id || idx} className="border-b border-slate-100">
                        <td className="px-3 py-2">
                          {canEdit ? (
                            <Input
                              value={item.description || ""}
                              onChange={(e) => updateLineItem(idx, "description", e.target.value)}
                              className="h-8 text-sm"
                            />
                          ) : (
                            item.description || "—"
                          )}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {canEdit ? (
                            <Input
                              type="number"
                              min={0}
                              step={0.01}
                              value={item.quantity ?? ""}
                              onChange={(e) => updateLineItem(idx, "quantity", e.target.value)}
                              className="h-8 w-20 text-right"
                            />
                          ) : (
                            item.quantity
                          )}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {canEdit ? (
                            <Input
                              type="number"
                              min={0}
                              step={0.01}
                              value={item.unit_price ?? ""}
                              onChange={(e) => updateLineItem(idx, "unit_price", e.target.value)}
                              className="h-8 w-24 text-right"
                            />
                          ) : (
                            `$${(item.unit_price ?? 0).toFixed(2)}`
                          )}
                        </td>
                        <td className="px-3 py-2 text-right font-mono">
                          ${(item.amount ?? item.quantity * item.unit_price ?? 0).toFixed(2)}
                        </td>
                        {canEdit && (
                          <td>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-600 h-8 w-8 p-0"
                              onClick={() => removeLineItem(idx)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Totals */}
            <div className="flex justify-end">
              <div className="w-64 space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Subtotal</span>
                  <span className="font-mono">${subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm items-center">
                  <span className="text-slate-500">Tax</span>
                  {canEdit ? (
                    <Input
                      type="number"
                      min={0}
                      step={0.01}
                      value={form.tax}
                      onChange={(e) => setForm((f) => ({ ...f, tax: e.target.value }))}
                      className="w-24 h-8 text-right"
                    />
                  ) : (
                    <span className="font-mono">${(parseFloat(form.tax) || 0).toFixed(2)}</span>
                  )}
                </div>
                <div className="flex justify-between font-bold pt-2 border-t">
                  <span>Total</span>
                  <span className="font-mono">${total.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label className="text-xs uppercase text-slate-500">Notes</Label>
              {canEdit ? (
                <Textarea
                  value={form.notes || ""}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  className="mt-1 min-h-[60px]"
                  placeholder="Optional notes"
                />
              ) : (
                <p className="mt-1 text-sm text-slate-600">{invoice?.notes || "—"}</p>
              )}
            </div>

            {/* Linked withdrawals */}
            {invoice?.withdrawal_ids?.length > 0 && (
              <div>
                <Label className="text-xs uppercase text-slate-500">Linked Withdrawals</Label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {invoice.withdrawal_ids.map((wid) => (
                    <span
                      key={wid}
                      className="px-2 py-1 bg-slate-100 rounded font-mono text-xs"
                      title={wid}
                    >
                      {wid.slice(0, 8)}…
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Status (for draft, allow changing to sent) */}
            {canEdit && (
              <div>
                <Label className="text-xs uppercase text-slate-500">Status</Label>
                <select
                  value={form.status}
                  onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                  className="mt-1 block w-40 rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="paid">Paid</option>
                </select>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-4 border-t">
          <div>
            {canEdit && (
              <Button
                variant="outline"
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                onClick={handleDeleteClick}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleSyncXero}>
              <ExternalLink className="w-4 h-4 mr-2" />
              Send to Xero
            </Button>
            {canEdit && (
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
    <ConfirmDialog
      open={deleteConfirmOpen}
      onOpenChange={setDeleteConfirmOpen}
      title="Delete draft invoice"
      description="Delete this draft invoice? Withdrawals will be unlinked."
      confirmLabel="Delete"
      cancelLabel="Cancel"
      onConfirm={handleDeleteConfirm}
      variant="danger"
    />
    </>
  );
}
