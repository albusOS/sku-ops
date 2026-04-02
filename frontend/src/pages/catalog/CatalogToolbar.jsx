import { useMemo, useState } from "react";
import { ChevronDown, LayoutGrid, List, Search, X, Plus, Printer, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

export function CatalogToolbar({
  searchInput,
  onSearchChange,
  categoryFilter,
  onCategoryChange,
  departments,
  viewMode,
  onViewModeChange,
  total,
  hasFilters,
  onClearFilters,
  isLoading,
  onAddProduct,
  onPrintLabels,
}) {
  const [categoriesOpen, setCategoriesOpen] = useState(false);

  const zeroCountCategories = useMemo(
    () => departments.filter((d) => (d.sku_count ?? 0) === 0).length,
    [departments],
  );

  const needsCollapsible = zeroCountCategories > 0;

  /** Most SKUs first; tie-break by name for stable order */
  const departmentsByProductCount = useMemo(() => {
    return [...departments].sort((a, b) => {
      const ca = a.sku_count ?? 0;
      const cb = b.sku_count ?? 0;
      if (cb !== ca) return cb - ca;
      return (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" });
    });
  }, [departments]);

  const activeCategoryName = useMemo(() => {
    if (!categoryFilter) return null;
    return departments.find((d) => d.id === categoryFilter)?.name ?? null;
  }, [departments, categoryFilter]);

  const renderPill = (dept) => {
    const count = dept.sku_count ?? 0;
    return (
      <button
        key={dept.id}
        type="button"
        onClick={() => onCategoryChange(dept.id === categoryFilter ? null : dept.id)}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all",
          dept.id === categoryFilter
            ? "bg-foreground text-background shadow-sm"
            : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        <span>{dept.name}</span>
        <span
          className={cn(
            "tabular-nums text-[10px] font-medium rounded-md px-1 py-px min-w-[1.125rem] text-center",
            dept.id === categoryFilter
              ? "bg-background/15 text-background/90"
              : "bg-background/40 text-muted-foreground",
          )}
        >
          {count}
        </span>
      </button>
    );
  };

  const pillRow = (deptList) => (
    <div className="flex flex-wrap items-center gap-1.5 gap-y-2">
      <button
        type="button"
        onClick={() => onCategoryChange(null)}
        className={cn(
          "px-3 py-1 rounded-full text-xs font-medium transition-all",
          !categoryFilter
            ? "bg-foreground text-background shadow-sm"
            : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        All
      </button>
      {deptList.map(renderPill)}
    </div>
  );

  const categoryHeaderInner = (
    <>
      <SlidersHorizontal className="w-4 h-4 text-muted-foreground shrink-0" />
      <span className="text-sm font-medium text-foreground">Product categories</span>
      {needsCollapsible && (
        <span className="text-xs text-muted-foreground font-normal tabular-nums">
          {categoriesOpen ? "Showing all" : `${departments.length} categories`}
        </span>
      )}
      {activeCategoryName && (
        <span className="text-xs text-accent font-medium truncate max-w-[140px]">
          · {activeCategoryName}
        </span>
      )}
    </>
  );

  return (
    <div className="space-y-3">
      {/* Primary toolbar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search products..."
            value={searchInput}
            onChange={(e) => onSearchChange(e.target.value)}
            className={cn(
              "w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-card",
              "text-sm text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent",
              "transition-colors",
            )}
          />
        </div>

        <div className="flex items-center rounded-lg border border-border bg-muted/40 p-0.5">
          <button
            type="button"
            onClick={() => onViewModeChange("cards")}
            className={cn(
              "p-1.5 rounded-md transition-all",
              viewMode === "cards"
                ? "bg-card shadow-sm text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
            title="Card view"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onViewModeChange("table")}
            className={cn(
              "p-1.5 rounded-md transition-all",
              viewMode === "table"
                ? "bg-card shadow-sm text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
            title="Table view"
          >
            <List className="w-4 h-4" />
          </button>
        </div>

        <div className="w-px h-6 bg-border" />

        <Button variant="outline" size="sm" className="gap-1.5 h-9" onClick={onPrintLabels}>
          <Printer className="w-4 h-4" />
          <span className="hidden sm:inline">Print Labels</span>
        </Button>
        <Button
          size="sm"
          className="btn-primary gap-1.5 h-9"
          onClick={onAddProduct}
          data-testid="add-product-btn"
        >
          <Plus className="w-4 h-4" />
          Add Product
        </Button>
      </div>

      {/* Category filters in a card */}
      <Card className="border-border/60 shadow-sm overflow-hidden">
        {needsCollapsible ? (
          <Collapsible open={categoriesOpen} onOpenChange={setCategoriesOpen}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 py-3 border-b border-border/50 bg-muted/20">
              <CollapsibleTrigger
                type="button"
                className={cn(
                  "flex items-center gap-2 text-left rounded-lg -mx-1 px-1 py-0.5",
                  "outline-none hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-accent/25",
                  "w-full sm:w-auto sm:min-w-0 flex-1",
                )}
              >
                {categoryHeaderInner}
                <ChevronDown
                  className={cn(
                    "w-4 h-4 text-muted-foreground shrink-0 ml-auto sm:ml-1 transition-transform duration-200",
                    categoriesOpen && "rotate-180",
                  )}
                />
              </CollapsibleTrigger>

              <div className="flex items-center justify-end gap-2 shrink-0 pl-1">
                {isLoading && (
                  <span className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                )}
                <span className="text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                  {total} products
                </span>
                {hasFilters && (
                  <button
                    type="button"
                    onClick={onClearFilters}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <X className="w-3 h-3" />
                    Clear
                  </button>
                )}
              </div>
            </div>

            <CollapsibleContent>
              <CardContent className="pt-4 pb-4">{pillRow(departmentsByProductCount)}</CardContent>
            </CollapsibleContent>
          </Collapsible>
        ) : (
          <>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 py-3 border-b border-border/50 bg-muted/20">
              <div className="flex items-center gap-2 min-w-0">{categoryHeaderInner}</div>
              <div className="flex items-center justify-end gap-2 shrink-0">
                {isLoading && (
                  <span className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                )}
                <span className="text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                  {total} products
                </span>
                {hasFilters && (
                  <button
                    type="button"
                    onClick={onClearFilters}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <X className="w-3 h-3" />
                    Clear
                  </button>
                )}
              </div>
            </div>
            <CardContent className="pt-4 pb-4">{pillRow(departmentsByProductCount)}</CardContent>
          </>
        )}
      </Card>
    </div>
  );
}
