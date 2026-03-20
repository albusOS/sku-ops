import { LayoutGrid, List, Search, X, Plus, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  return (
    <div className="space-y-3">
      {/* Primary toolbar */}
      <div className="flex items-center gap-3">
        {/* Search */}
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

        {/* View toggle */}
        <div className="flex items-center rounded-lg border border-border bg-muted/40 p-0.5">
          <button
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

        {/* Actions */}
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

      {/* Category filter pills */}
      <div className="flex flex-wrap items-center gap-1.5">
        <button
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
        {departments.map((dept) => (
          <button
            key={dept.id}
            onClick={() => onCategoryChange(dept.id === categoryFilter ? null : dept.id)}
            className={cn(
              "px-3 py-1 rounded-full text-xs font-medium transition-all",
              dept.id === categoryFilter
                ? "bg-foreground text-background shadow-sm"
                : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {dept.name}
            {dept.sku_count != null && <span className="ml-1 opacity-60">{dept.sku_count}</span>}
          </button>
        ))}

        {/* Result count + clear */}
        <div className="flex items-center gap-2 ml-auto">
          {isLoading && (
            <span className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          )}
          <span className="text-xs text-muted-foreground tabular-nums">{total} products</span>
          {hasFilters && (
            <button
              onClick={onClearFilters}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <X className="w-3 h-3" />
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
