import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { FileText, Plus, Filter, Send } from "lucide-react";
import { format } from "date-fns";
import { CreateInvoiceModal } from "../components/CreateInvoiceModal";
import { InvoiceDetailModal } from "../components/InvoiceDetailModal";
import { API } from "@/lib/api";

const Invoices = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailInvoiceId, setDetailInvoiceId] = useState(null);
  const [sendingXero, setSendingXero] = useState(null);

  useEffect(() => {
    fetchInvoices();
  }, [statusFilter, entityFilter]);

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      if (entityFilter) params.append("billing_entity", entityFilter);
      const res = await axios.get(`${API}/invoices?${params}`);
      setInvoices(res.data);
    } catch (err) {
      toast.error("Failed to load invoices");
    } finally {
      setLoading(false);
    }
  };

  const billingEntities = [...new Set(invoices.map((i) => i.billing_entity).filter(Boolean))].sort();

  const handleInvoiceCreated = () => {
    fetchInvoices();
  };

  const handleInvoiceSaved = () => {
    fetchInvoices();
  };

  const handleInvoiceDeleted = () => {
    setDetailInvoiceId(null);
    fetchInvoices();
  };

  const handleSendToXero = async (invoiceId, e) => {
    e?.stopPropagation();
    setSendingXero(invoiceId);
    try {
      const res = await axios.post(`${API}/invoices/${invoiceId}/sync-xero`);
      toast.info(res.data?.message || "Xero integration coming soon");
    } catch (err) {
      toast.error("Failed to send to Xero");
    } finally {
      setSendingXero(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-slate-600 font-heading text-xl uppercase tracking-wider">
          Loading Invoices...
        </div>
      </div>
    );
  }

  return (
    <div className="p-8" data-testid="invoices-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading font-bold text-3xl text-slate-900 uppercase tracking-wider">
            Invoices
          </h1>
          <p className="text-slate-600 mt-1">View and edit invoice records</p>
        </div>
        <Button
          onClick={() => setCreateModalOpen(true)}
          className="btn-primary h-12"
          data-testid="create-invoice-btn"
        >
          <Plus className="w-5 h-5 mr-2" />
          Create Invoice
        </Button>
      </div>

      {/* Filters */}
      <div className="card-workshop p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-slate-400" />
            <span className="text-sm text-slate-600 font-semibold uppercase">Filters:</span>
          </div>
          <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[140px] input-workshop">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="sent">Sent</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
            </SelectContent>
          </Select>
          <Select value={entityFilter || "all"} onValueChange={(v) => setEntityFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[180px] input-workshop">
              <SelectValue placeholder="All Entities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Entities</SelectItem>
              {billingEntities.map((entity) => (
                <SelectItem key={entity} value={entity}>
                  {entity}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {(statusFilter || entityFilter) && (
            <Button
              variant="ghost"
              onClick={() => {
                setStatusFilter("");
                setEntityFilter("");
              }}
              className="text-slate-500"
            >
              Clear Filters
            </Button>
          )}
        </div>
      </div>

      {/* Invoice list */}
      <div className="card-workshop overflow-hidden">
        <table className="w-full table-workshop">
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Billing Entity</th>
              <th>Total</th>
              <th>Status</th>
              <th>Date</th>
              <th>Withdrawals</th>
              <th className="w-[140px]">Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.length === 0 ? (
              <tr>
                <td colSpan="7" className="text-center py-12 text-slate-400">
                  No invoices yet. Invoices are auto-created when withdrawals are made.
                </td>
              </tr>
            ) : (
              invoices.map((inv) => (
                <tr
                  key={inv.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => setDetailInvoiceId(inv.id)}
                >
                  <td className="font-mono font-medium">{inv.invoice_number}</td>
                  <td>{inv.billing_entity || "—"}</td>
                  <td className="font-mono font-bold">${(inv.total ?? 0).toFixed(2)}</td>
                  <td>
                    <span
                      className={`px-2 py-1 rounded-sm text-xs font-bold uppercase ${
                        inv.status === "draft"
                          ? "bg-slate-200 text-slate-700"
                          : inv.status === "sent"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-green-100 text-green-700"
                      }`}
                    >
                      {inv.status}
                    </span>
                  </td>
                  <td className="font-mono text-sm">
                    {inv.created_at ? format(new Date(inv.created_at), "MMM d, yyyy") : "—"}
                  </td>
                  <td className="font-mono text-slate-600">{inv.withdrawal_count ?? 0}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDetailInvoiceId(inv.id);
                        }}
                      >
                        <FileText className="w-4 h-4 mr-1" />
                        View
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => handleSendToXero(inv.id, e)}
                        disabled={sendingXero === inv.id}
                        className="text-blue-600 border-blue-200 hover:bg-blue-50"
                      >
                        <Send className="w-4 h-4 mr-1" />
                        {sendingXero === inv.id ? "…" : "Send to Xero"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <CreateInvoiceModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        onCreated={(inv) => {
          handleInvoiceCreated();
          setDetailInvoiceId(inv?.id);
        }}
      />

      <InvoiceDetailModal
        invoiceId={detailInvoiceId}
        open={!!detailInvoiceId}
        onOpenChange={(open) => !open && setDetailInvoiceId(null)}
        onSaved={handleInvoiceSaved}
        onDeleted={handleInvoiceDeleted}
      />
    </div>
  );
};

export default Invoices;
