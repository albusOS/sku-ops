import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Calendar } from "../components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  DollarSign,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Download,
  Calendar as CalendarIcon,
  Filter,
  Building2,
  HardHat,
  FileText,
} from "lucide-react";
import { format } from "date-fns";
import { Card, Metric, DonutChart, BarList } from "@tremor/react";

import { Link } from "react-router-dom";
import { API } from "@/lib/api";
import { valueFormatter, CHART_COLORS } from "@/lib/chartConfig";
import { CreateInvoiceModal } from "../components/CreateInvoiceModal";

const Financials = () => {
  const [summary, setSummary] = useState(null);
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [dateRange, setDateRange] = useState({ from: null, to: null });
  const [createInvoiceModalOpen, setCreateInvoiceModalOpen] = useState(false);

  useEffect(() => {
    fetchData();
  }, [statusFilter, entityFilter, dateRange]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("payment_status", statusFilter);
      if (entityFilter) params.append("billing_entity", entityFilter);
      if (dateRange.from) params.append("start_date", dateRange.from.toISOString());
      if (dateRange.to) params.append("end_date", dateRange.to.toISOString());

      const [summaryRes, withdrawalsRes] = await Promise.all([
        axios.get(`${API}/financials/summary?${params}`),
        axios.get(`${API}/withdrawals?${params}`),
      ]);

      setSummary(summaryRes.data);
      setWithdrawals(withdrawalsRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Failed to load financial data");
    } finally {
      setLoading(false);
    }
  };

  const handleMarkPaid = async (withdrawalId) => {
    try {
      await axios.put(`${API}/withdrawals/${withdrawalId}/mark-paid`);
      toast.success("Marked as paid");
      fetchData();
    } catch (error) {
      toast.error("Failed to mark as paid");
    }
  };

  const handleBulkMarkPaid = async () => {
    if (selectedIds.length === 0) {
      toast.error("No transactions selected");
      return;
    }
    try {
      await axios.put(`${API}/withdrawals/bulk-mark-paid`, selectedIds);
      toast.success(`Marked ${selectedIds.length} transactions as paid`);
      setSelectedIds([]);
      fetchData();
    } catch (error) {
      toast.error("Failed to mark as paid");
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("payment_status", statusFilter);
      if (entityFilter) params.append("billing_entity", entityFilter);
      if (dateRange.from) params.append("start_date", dateRange.from.toISOString());
      if (dateRange.to) params.append("end_date", dateRange.to.toISOString());

      const response = await axios.get(`${API}/financials/export?${params}`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `financials_${format(new Date(), "yyyyMMdd")}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Export downloaded");
    } catch (error) {
      toast.error("Failed to export");
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectAllUnpaid = () => {
    const unpaidIds = withdrawals
      .filter((w) => w.payment_status === "unpaid" && !w.invoice_id)
      .map((w) => w.id);
    setSelectedIds(unpaidIds);
  };

  const selectedUnpaidIds = selectedIds.filter((id) => {
    const w = withdrawals.find((x) => x.id === id);
    return w?.payment_status === "unpaid" && !w?.invoice_id;
  });

  const handleInvoiceCreated = () => {
    setSelectedIds([]);
    fetchData();
  };

  // Get unique billing entities for filter
  const billingEntities = [...new Set(withdrawals.map((w) => w.billing_entity).filter(Boolean))];

  const paymentDonutData = summary
    ? [
        { name: "Paid", value: summary.total_paid || 0 },
        { name: "Unpaid", value: summary.total_unpaid || 0 },
        { name: "Invoiced", value: summary.total_invoiced || 0 },
      ].filter((d) => d.value > 0)
    : [];

  const contractorBarData = summary?.by_contractor
    ? summary.by_contractor
        .sort((a, b) => (b.total || 0) - (a.total || 0))
        .slice(0, 10)
        .map((c) => ({
          name: c.name || c.company || "Unknown",
          value: c.total || 0,
        }))
    : [];

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-slate-600 font-heading text-xl uppercase tracking-wider">
          Loading Financials...
        </div>
      </div>
    );
  }

  return (
    <div className="p-8" data-testid="financials-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading font-bold text-3xl text-slate-900 uppercase tracking-wider">
            Financial Dashboard
          </h1>
          <p className="text-slate-600 mt-1">Track payments, invoicing, and exports</p>
        </div>
        <div className="flex gap-3">
          <Button
            onClick={handleExport}
            variant="outline"
            className="btn-secondary h-12"
            data-testid="export-btn"
          >
            <Download className="w-5 h-5 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8" data-testid="summary-cards">
        <Card className="card-workshop">
          <Metric color="rose">{valueFormatter(summary?.total_unpaid || 0)}</Metric>
          <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Unpaid</p>
        </Card>
        <Card className="card-workshop">
          <Metric color="emerald">{valueFormatter(summary?.total_paid || 0)}</Metric>
          <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Paid</p>
        </Card>
        <Card className="card-workshop">
          <Metric>{valueFormatter(summary?.total_revenue || 0)}</Metric>
          <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Total Revenue</p>
        </Card>
        <Card className="card-workshop">
          <Metric color="violet">{valueFormatter(summary?.gross_margin || 0)}</Metric>
          <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Gross Margin</p>
        </Card>
      </div>

      {/* Donut + BarList Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="card-workshop p-6">
          <h2 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider mb-4">
            Payment Status
          </h2>
          {paymentDonutData.length > 0 ? (
            <DonutChart
              data={paymentDonutData}
              category="value"
              index="name"
              valueFormatter={valueFormatter}
              colors={CHART_COLORS}
              className="h-64"
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-400">
              No payment data
            </div>
          )}
        </Card>
        <Card className="card-workshop p-6">
          <h2 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider mb-4">
            Top Contractors by Spend
          </h2>
          {contractorBarData.length > 0 ? (
            <BarList
              data={contractorBarData}
              valueFormatter={valueFormatter}
              className="mt-2"
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-400">
              No contractor data
            </div>
          )}
        </Card>
      </div>

      {/* By Entity Breakdown */}
      {summary?.by_billing_entity && Object.keys(summary.by_billing_entity).length > 0 && (
        <Card className="card-workshop p-6 mb-6">
          <h2 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider mb-4">
            By Billing Entity
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(summary.by_billing_entity).map(([entity, data]) => (
              <div key={entity} className="p-4 bg-slate-50 rounded-sm border border-slate-200">
                <div className="flex items-center gap-2 mb-2">
                  <Building2 className="w-4 h-4 text-slate-400" />
                  <span className="font-semibold text-slate-900">{entity}</span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total</span>
                    <span className="font-mono">${data.total.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-red-500">Unpaid</span>
                    <span className="font-mono text-red-600">${data.unpaid.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Transactions</span>
                    <span className="font-mono">{data.count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Filters */}
      <div className="card-workshop p-4 mb-6" data-testid="filters">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-slate-400" />
            <span className="text-sm text-slate-600 font-semibold uppercase">Filters:</span>
          </div>

          <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[150px] input-workshop">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="unpaid">Unpaid</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
              <SelectItem value="invoiced">Invoiced</SelectItem>
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

          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="btn-secondary h-12">
                <CalendarIcon className="w-5 h-5 mr-2" />
                {dateRange.from ? (
                  dateRange.to ? (
                    <>
                      {format(dateRange.from, "MMM d")} - {format(dateRange.to, "MMM d")}
                    </>
                  ) : (
                    format(dateRange.from, "MMM d, yyyy")
                  )
                ) : (
                  "Date Range"
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="range"
                selected={dateRange}
                onSelect={(range) => setDateRange(range || { from: null, to: null })}
                numberOfMonths={2}
              />
            </PopoverContent>
          </Popover>

          {(statusFilter || entityFilter || dateRange.from) && (
            <Button
              variant="ghost"
              onClick={() => {
                setStatusFilter("");
                setEntityFilter("");
                setDateRange({ from: null, to: null });
              }}
              className="text-slate-500"
            >
              Clear Filters
            </Button>
          )}
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedIds.length > 0 && (
        <div className="card-workshop p-4 mb-4 bg-orange-50 border-orange-200 flex items-center justify-between">
          <span className="font-semibold text-orange-700">
            {selectedIds.length} transaction(s) selected
          </span>
          <div className="flex gap-3">
            <Button
              variant="ghost"
              onClick={() => setSelectedIds([])}
              className="text-slate-600"
            >
              Clear Selection
            </Button>
            {selectedUnpaidIds.length > 0 && (
              <Button
                variant="outline"
                onClick={() => setCreateInvoiceModalOpen(true)}
                className="btn-secondary"
              >
                <FileText className="w-4 h-4 mr-2" />
                Create Invoice ({selectedUnpaidIds.length})
              </Button>
            )}
            <Button
              onClick={handleBulkMarkPaid}
              className="btn-primary"
              data-testid="bulk-mark-paid-btn"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Mark All Paid
            </Button>
          </div>
        </div>
      )}

      <CreateInvoiceModal
        open={createInvoiceModalOpen}
        onOpenChange={setCreateInvoiceModalOpen}
        onCreated={handleInvoiceCreated}
        preselectedIds={selectedUnpaidIds}
      />

      {/* Transactions Table */}
      <div className="card-workshop overflow-hidden" data-testid="transactions-table">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider">
            Transactions ({withdrawals.length})
          </h2>
          <Button
            variant="ghost"
            onClick={selectAllUnpaid}
            className="text-sm text-orange-600"
          >
            Select All Unpaid
          </Button>
        </div>
        <table className="w-full table-workshop">
          <thead>
            <tr>
              <th className="w-10"></th>
              <th>Date</th>
              <th>Contractor</th>
              <th>Job ID</th>
              <th>Service Address</th>
              <th>Total</th>
              <th>Cost</th>
              <th>Margin</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {withdrawals.length === 0 ? (
              <tr>
                <td colSpan="10" className="text-center py-12 text-slate-400">
                  No transactions found
                </td>
              </tr>
            ) : (
              withdrawals.map((w) => (
                <tr key={w.id} data-testid={`transaction-row-${w.id}`}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(w.id)}
                      onChange={() => toggleSelect(w.id)}
                      disabled={!!w.invoice_id}
                      className="w-4 h-4 rounded border-slate-300 disabled:opacity-50"
                    />
                  </td>
                  <td className="font-mono text-sm">
                    {new Date(w.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <HardHat className="w-4 h-4 text-slate-400" />
                      <div>
                        <p className="font-medium">{w.contractor_name}</p>
                        <p className="text-xs text-slate-400">{w.contractor_company}</p>
                      </div>
                    </div>
                  </td>
                  <td className="font-mono text-sm">{w.job_id}</td>
                  <td className="text-sm max-w-[200px] truncate" title={w.service_address}>
                    {w.service_address}
                  </td>
                  <td className="font-mono font-bold">${w.total.toFixed(2)}</td>
                  <td className="font-mono text-slate-500 text-sm">${(w.cost_total || 0).toFixed(2)}</td>
                  <td className="font-mono text-green-600 text-sm">${((w.total || 0) - (w.cost_total || 0)).toFixed(2)}</td>
                  <td>
                    {w.payment_status === "paid" ? (
                      <span className="badge-success">Paid</span>
                    ) : w.payment_status === "invoiced" && w.invoice_id ? (
                      <Link
                        to="/invoices"
                        className="bg-blue-600 text-white px-2 py-1 rounded-sm text-xs font-bold uppercase hover:bg-blue-700 hover:underline"
                      >
                        Invoiced
                      </Link>
                    ) : w.payment_status === "invoiced" ? (
                      <span className="bg-blue-600 text-white px-2 py-1 rounded-sm text-xs font-bold uppercase">
                        Invoiced
                      </span>
                    ) : (
                      <span className="badge-warning">Unpaid</span>
                    )}
                  </td>
                  <td>
                    {w.payment_status === "unpaid" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMarkPaid(w.id)}
                        className="text-green-600 hover:text-green-700 hover:bg-green-50"
                        data-testid={`mark-paid-${w.id}`}
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Mark Paid
                      </Button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Financials;
