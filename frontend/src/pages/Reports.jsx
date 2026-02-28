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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  BarChart3,
  TrendingUp,
  Package,
  DollarSign,
  Calendar as CalendarIcon,
  AlertTriangle,
  ShoppingCart,
  Download,
} from "lucide-react";
import { format } from "date-fns";
import { Card, Metric, DonutChart, BarList } from "@tremor/react";

import { API } from "@/lib/api";
import { valueFormatter, CHART_COLORS } from "@/lib/chartConfig";

const DATE_PRESETS = [
  { label: "Today", getValue: () => { const d = new Date(); return { from: d, to: d }; } },
  { label: "Last 7 days", getValue: () => { const end = new Date(); const start = new Date(end); start.setDate(start.getDate() - 6); return { from: start, to: end }; } },
  { label: "This month", getValue: () => { const end = new Date(); const start = new Date(end.getFullYear(), end.getMonth(), 1); return { from: start, to: end }; } },
  { label: "All time", getValue: () => ({ from: null, to: null }) },
];

const Reports = () => {
  const [activeTab, setActiveTab] = useState("sales");
  const [salesReport, setSalesReport] = useState(null);
  const [inventoryReport, setInventoryReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({
    from: null,
    to: null,
  });

  useEffect(() => {
    fetchReports();
  }, [dateRange]);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateRange.from) {
        params.append("start_date", dateRange.from.toISOString());
      }
      if (dateRange.to) {
        params.append("end_date", dateRange.to.toISOString());
      }

      const [salesRes, inventoryRes] = await Promise.all([
        axios.get(`${API}/reports/sales?${params}`),
        axios.get(`${API}/reports/inventory`),
      ]);

      setSalesReport(salesRes.data);
      setInventoryReport(inventoryRes.data);
    } catch (error) {
      console.error("Error fetching reports:", error);
      toast.error("Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  const paymentChartData = salesReport?.by_payment_status
    ? Object.entries(salesReport.by_payment_status).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value: parseFloat(value.toFixed(2)),
      }))
    : [];

  const handleExportCSV = () => {
    const rows = [];
    if (activeTab === "sales" && salesReport) {
      rows.push(["Report", "Sales Report"]);
      rows.push(["Date Range", dateRange.from ? (dateRange.to ? `${format(dateRange.from, "yyyy-MM-dd")} to ${format(dateRange.to, "yyyy-MM-dd")}` : format(dateRange.from, "yyyy-MM-dd")) : "All time"]);
      rows.push([]);
      rows.push(["Metric", "Value"]);
      rows.push(["Total Revenue", salesReport.total_revenue]);
      rows.push(["Total Transactions", salesReport.total_transactions]);
      rows.push(["Average Transaction", salesReport.average_transaction]);
      rows.push(["Total Tax", salesReport.total_tax]);
      if (salesReport.top_products?.length) {
        rows.push([]);
        rows.push(["Top Products", "Name", "Revenue", "Quantity"]);
        salesReport.top_products.forEach((p) => rows.push([p.name, p.revenue, p.quantity]));
      }
    } else if (activeTab === "inventory" && inventoryReport) {
      rows.push(["Report", "Inventory Report"]);
      rows.push([]);
      rows.push(["Metric", "Value"]);
      rows.push(["Total Products", inventoryReport.total_products]);
      rows.push(["Retail Value", inventoryReport.total_retail_value]);
      rows.push(["Cost Value", inventoryReport.total_cost_value]);
      rows.push(["Potential Profit", inventoryReport.potential_profit]);
      rows.push(["Low Stock Count", inventoryReport.low_stock_count]);
      rows.push(["Out of Stock Count", inventoryReport.out_of_stock_count]);
    }
    const csv = rows.map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${activeTab}-${format(new Date(), "yyyy-MM-dd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const departmentChartData = inventoryReport?.by_department
    ? Object.entries(inventoryReport.by_department).map(([name, data]) => ({
        name,
        count: data.count,
        value: parseFloat(data.value.toFixed(2)),
      }))
    : [];

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-slate-600 font-heading text-xl uppercase tracking-wider">
          Loading Reports...
        </div>
      </div>
    );
  }

  return (
    <div className="p-8" data-testid="reports-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading font-bold text-3xl text-slate-900 uppercase tracking-wider">
            Reports
          </h1>
          <p className="text-slate-600 mt-1">Sales and inventory analytics</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Date Presets */}
          <div className="flex gap-1">
            {DATE_PRESETS.map((preset) => (
              <Button
                key={preset.label}
                variant="outline"
                size="sm"
                onClick={() => setDateRange(preset.getValue())}
              >
                {preset.label}
              </Button>
            ))}
          </div>
          {/* Date Range Picker */}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="btn-secondary h-12 px-4" data-testid="date-range-btn">
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
                  "All Time"
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="range"
                selected={dateRange}
                onSelect={(range) => setDateRange(range || { from: null, to: null })}
                numberOfMonths={2}
              />
            </PopoverContent>
          </Popover>
          {(dateRange.from || dateRange.to) && (
            <Button
              variant="ghost"
              onClick={() => setDateRange({ from: null, to: null })}
              className="h-12"
              data-testid="clear-date-btn"
            >
              Clear
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleExportCSV} data-testid="export-csv-btn">
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="bg-slate-100 p-1 h-auto" data-testid="report-tabs">
          <TabsTrigger
            value="sales"
            className="px-6 py-3 font-heading uppercase tracking-wide data-[state=active]:bg-white data-[state=active]:shadow-hard-sm"
            data-testid="sales-tab"
          >
            <BarChart3 className="w-5 h-5 mr-2" />
            Sales Report
          </TabsTrigger>
          <TabsTrigger
            value="inventory"
            className="px-6 py-3 font-heading uppercase tracking-wide data-[state=active]:bg-white data-[state=active]:shadow-hard-sm"
            data-testid="inventory-tab"
          >
            <Package className="w-5 h-5 mr-2" />
            Inventory Report
          </TabsTrigger>
        </TabsList>

        {/* Sales Report Tab */}
        <TabsContent value="sales" className="space-y-6" data-testid="sales-report-content">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="card-workshop">
              <Metric color="emerald">{valueFormatter(salesReport?.total_revenue || 0)}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Total Revenue</p>
            </Card>
            <Card className="card-workshop">
              <Metric color="blue">{salesReport?.total_transactions || 0}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Transactions</p>
            </Card>
            <Card className="card-workshop">
              <Metric color="violet">{valueFormatter(salesReport?.average_transaction || 0)}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Avg Transaction</p>
            </Card>
            <Card className="card-workshop">
              <Metric color="orange">{valueFormatter(salesReport?.total_tax || 0)}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Total Tax</p>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Payment Status - Donut Chart */}
            <Card className="card-workshop p-6">
              <h3 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider mb-4">
                Sales by Payment Status
              </h3>
              {paymentChartData.length > 0 ? (
                <DonutChart
                  data={paymentChartData}
                  category="value"
                  index="name"
                  valueFormatter={valueFormatter}
                  colors={CHART_COLORS}
                  className="h-[300px]"
                />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-400">
                  No sales data available
                </div>
              )}
            </Card>

            {/* Top Products - BarList */}
            <Card className="card-workshop p-6">
              <h3 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider mb-4">
                Top Selling Products
              </h3>
              {salesReport?.top_products?.length > 0 ? (
                <BarList
                  data={salesReport.top_products.slice(0, 10).map((p) => ({
                    name: p.name,
                    value: p.revenue,
                  }))}
                  valueFormatter={valueFormatter}
                  className="mt-2"
                />
              ) : (
                <div className="h-[250px] flex items-center justify-center text-slate-400">
                  No sales data available
                </div>
              )}
            </Card>
          </div>
        </TabsContent>

        {/* Inventory Report Tab */}
        <TabsContent value="inventory" className="space-y-6" data-testid="inventory-report-content">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="card-workshop">
              <Metric color="blue">{inventoryReport?.total_products || 0}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Total Products</p>
            </Card>
            <Card className="card-workshop">
              <Metric color="emerald">{valueFormatter(inventoryReport?.total_retail_value || 0)}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Retail Value</p>
            </Card>
            <Card className="card-workshop">
              <Metric color="violet">{valueFormatter(inventoryReport?.potential_profit || 0)}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Potential Profit</p>
            </Card>
            <Card className="card-workshop">
              <Metric color="amber">{inventoryReport?.low_stock_count || 0}</Metric>
              <p className="text-sm text-slate-500 uppercase tracking-wide mt-1">Low Stock Items</p>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Inventory by Department - BarList */}
            <Card className="card-workshop p-6">
              <h3 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider mb-4">
                Inventory Value by Department
              </h3>
              {departmentChartData.length > 0 ? (
                <BarList
                  data={departmentChartData.map((d) => ({ name: d.name, value: d.value }))}
                  valueFormatter={valueFormatter}
                  className="mt-2"
                />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-400">
                  No inventory data available
                </div>
              )}
            </Card>

            {/* Low Stock Items */}
            <Card className="card-workshop p-6">
              <h3 className="font-heading font-bold text-lg text-slate-900 uppercase tracking-wider mb-4">
                Low Stock Alert
              </h3>
              {inventoryReport?.low_stock_items?.length > 0 ? (
                <div className="space-y-3 max-h-[300px] overflow-auto">
                  {inventoryReport.low_stock_items.map((item, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-orange-50 rounded-sm border border-orange-200"
                    >
                      <div>
                        <p className="font-mono text-sm text-orange-700">{item.sku}</p>
                        <p className="font-medium text-slate-800">{item.name}</p>
                      </div>
                      <div className="text-right">
                        <span className="badge-warning">{item.quantity} left</span>
                        <p className="text-xs text-slate-500 mt-1">Min: {item.min_stock}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-slate-400">
                  <div className="text-center">
                    <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>All products are well stocked</p>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Reports;
