import { useState, useMemo } from "react";
import { Calendar as CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
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
    <div className="p-6 md:p-10" data-testid="reports-page">
      <div className="max-w-[1600px] mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-10">
          <div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Reports</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Revenue, margins, inventory health, and product performance — click any card to drill
              in
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

        <div className="space-y-8">
          <section>
            <h2 className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground border-l-2 border-accent pl-3 mb-4">
              Financial
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
              <ProfitCard dateParams={dateParams} reportFilters={reportFilters} />
              <RevenueTrendCard reportFilters={reportFilters} />
            </div>
          </section>

          <section>
            <h2 className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground border-l-2 border-category-2 pl-3 mb-4">
              Inventory & Operations
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
              <InventoryHealthCard dateParams={dateParams} onProductClick={handleProductClick} />
              <StockPulseCard />
            </div>
          </section>

          <section>
            <h2 className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground border-l-2 border-category-4 pl-3 mb-4">
              Product Intelligence
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
              <PortfolioCard dateParams={dateParams} onProductClick={handleProductClick} />
              <TopPerformersCard dateParams={dateParams} />
            </div>
          </section>
        </div>
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
