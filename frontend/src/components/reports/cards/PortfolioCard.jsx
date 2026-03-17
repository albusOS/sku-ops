import { useState, useMemo } from "react";
import { useReportProductPerformance } from "@/hooks/useReports";
import { ProductBubblePlot } from "@/components/charts/ProductBubblePlot";
import { BentoCard } from "../BentoCard";
import { ReportDetailModal, Narrative } from "../ReportDetailModal";

function QuadrantStats({ products }) {
  const stats = useMemo(() => {
    const stars = products.filter(
      (p) => (p.sell_through_pct ?? 0) >= 50 && (p.margin_pct ?? 0) >= 40,
    );
    const review = products.filter(
      (p) => (p.sell_through_pct ?? 0) < 50 && (p.margin_pct ?? 0) < 40,
    );
    const slowMovers = products.filter(
      (p) => (p.sell_through_pct ?? 0) < 50 && (p.margin_pct ?? 0) >= 40,
    );
    const volumeDrivers = products.filter(
      (p) => (p.sell_through_pct ?? 0) >= 50 && (p.margin_pct ?? 0) < 40,
    );
    return { stars, review, slowMovers, volumeDrivers };
  }, [products]);

  const items = [
    { label: "Stars", count: stats.stars.length, color: "text-success" },
    { label: "Volume Drivers", count: stats.volumeDrivers.length, color: "text-info" },
    { label: "Slow Movers", count: stats.slowMovers.length, color: "text-category-5" },
    { label: "Review", count: stats.review.length, color: "text-destructive" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map((q) => (
        <div key={q.label} className="bg-muted/40 rounded-lg p-3 text-center">
          <p className={`text-lg font-bold tabular-nums ${q.color}`}>{q.count}</p>
          <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
            {q.label}
          </p>
        </div>
      ))}
    </div>
  );
}

export function PortfolioCard({ dateParams, onProductClick }) {
  const [open, setOpen] = useState(false);
  const { data: perfData } = useReportProductPerformance(dateParams);
  const products = useMemo(() => perfData?.products || [], [perfData]);

  const quadrants = useMemo(() => {
    const review = products.filter(
      (p) => (p.sell_through_pct ?? 0) < 50 && (p.margin_pct ?? 0) < 40,
    );
    const stars = products.filter(
      (p) => (p.sell_through_pct ?? 0) >= 50 && (p.margin_pct ?? 0) >= 40,
    );
    return { review: review.length, stars: stars.length };
  }, [products]);

  const narrativeItems = useMemo(() => {
    if (!products.length) return [];
    const items = [];
    items.push(`${products.length} products plotted by sell-through rate vs margin.`);
    if (quadrants.stars > 0)
      items.push(`${quadrants.stars} star products — high sell-through and high margin.`);
    if (quadrants.review > 0)
      items.push(
        `${quadrants.review} products in the review quadrant — low sell-through and low margin. Consider repricing or discontinuing.`,
      );
    return items;
  }, [products, quadrants]);

  const insight =
    products.length > 0
      ? `${products.length} products · ${quadrants.stars} stars · ${quadrants.review} need review`
      : "Loading...";

  const portfolioStatus =
    products.length > 0
      ? quadrants.review > quadrants.stars
        ? "warn"
        : quadrants.stars > 0
          ? "healthy"
          : undefined
      : undefined;

  return (
    <>
      <BentoCard
        title="Product Portfolio"
        metric={products.length > 0 ? `${products.length} products` : "—"}
        insight={insight}
        status={portfolioStatus}
        size="large"
        onClick={() => setOpen(true)}
      >
        {products.length > 0 ? (
          <ProductBubblePlot products={products} height={180} />
        ) : (
          <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
            No product data
          </div>
        )}
      </BentoCard>

      <ReportDetailModal
        open={open}
        onClose={() => setOpen(false)}
        title="Product Portfolio Analysis"
        subtitle="Sell-through vs margin — bubble size shows revenue"
      >
        {products.length > 0 && (
          <ProductBubblePlot products={products} onBubbleClick={onProductClick} height={460} />
        )}
        <QuadrantStats products={products} />
        <Narrative items={narrativeItems} />
      </ReportDetailModal>
    </>
  );
}
