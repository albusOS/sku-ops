import { useState, useMemo } from "react";
import { Calendar as CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { format } from "date-fns";
import { DATE_PRESETS } from "@/lib/constants";
import { dateToISO, endOfDayISO } from "@/lib/utils";
import { ProductDetailModal } from "@/components/ProductDetailModal";
import { ProfitCard } from "@/components/reports/cards/ProfitCard";
import { RevenueTrendCard } from "@/components/reports/cards/RevenueTrendCard";
import { PortfolioCard } from "@/components/reports/cards/PortfolioCard";
import { StockPulseCard } from "@/components/reports/cards/StockPulseCard";
import { InventoryHealthCard } from "@/components/reports/cards/InventoryHealthCard";
import { TopPerformersCard } from "@/components/reports/cards/TopPerformersCard";

const Reports = () => {
  const [dateRange, setDateRange] = useState({ from: null, to: null });
  const [selectedProduct, setSelectedProduct] = useState(null);

  const dateParams = useMemo(
    () => ({
      start_date: dateToISO(dateRange.from),
      end_date: endOfDayISO(dateRange.to),
    }),
    [dateRange],
  );

  const reportFilters = useMemo(() => ({ ...dateParams }), [dateParams]);

  const handleProductClick = (product) => {
    setSelectedProduct({
      id: product.product_id || product.id,
      name: product.name,
      sku: product.sku,
    });
  };

  return (
    <div className="p-6 md:p-8" data-testid="reports-page">
      <div className="max-w-[1400px] mx-auto">
        {/* Header with date controls */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Reports</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Financial performance, inventory health, and product intelligence
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
              {DATE_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => setDateRange(preset.getValue())}
                  className="text-xs px-3 py-1.5 rounded-md text-muted-foreground hover:bg-card hover:shadow-sm transition-all font-medium"
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2" data-testid="date-range-btn">
                  <CalendarIcon className="w-4 h-4" />
                  {dateRange.from
                    ? dateRange.to
                      ? `${format(dateRange.from, "MMM d")} – ${format(dateRange.to, "MMM d")}`
                      : format(dateRange.from, "MMM d, yyyy")
                    : "Custom"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="end">
                <Calendar
                  mode="range"
                  selected={dateRange}
                  onSelect={(r) => setDateRange(r || { from: null, to: null })}
                  numberOfMonths={2}
                />
              </PopoverContent>
            </Popover>
            {(dateRange.from || dateRange.to) && (
              <button
                onClick={() => setDateRange({ from: null, to: null })}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="inventory">Inventory</TabsTrigger>
            <TabsTrigger value="products">Products</TabsTrigger>
          </TabsList>

          {/* Overview tab — financial KPIs */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2">
                <ProfitCard dateParams={dateParams} reportFilters={reportFilters} />
              </div>
              <div className="lg:col-span-1">
                <RevenueTrendCard reportFilters={reportFilters} />
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <StockPulseCard />
              <TopPerformersCard dateParams={dateParams} />
            </div>
          </TabsContent>

          {/* Inventory tab — stock-focused */}
          <TabsContent value="inventory" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <InventoryHealthCard dateParams={dateParams} onProductClick={handleProductClick} />
              <StockPulseCard />
            </div>
          </TabsContent>

          {/* Products tab — performance & portfolio */}
          <TabsContent value="products" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <PortfolioCard dateParams={dateParams} onProductClick={handleProductClick} />
              <TopPerformersCard dateParams={dateParams} />
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <ProductDetailModal
        product={selectedProduct}
        open={!!selectedProduct}
        onOpenChange={(open) => !open && setSelectedProduct(null)}
      />
    </div>
  );
};

export default Reports;
