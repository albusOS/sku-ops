import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

/**
 * Popover with checkboxes to show/hide report panels.
 * Persisted via useReportLayout.
 */
export function ReportLayoutCustomizer({
  panels,
  visiblePanels,
  setPanelVisible,
  resetToDefault,
  className,
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn("gap-2 text-muted-foreground hover:text-foreground", className)}
        >
          <SlidersHorizontal className="w-4 h-4" />
          Customize view
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-0" align="end">
        <div className="p-3 border-b border-border">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Show panels
          </p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Toggle charts and graphs to reduce clutter
          </p>
        </div>
        <div className="p-2 max-h-[280px] overflow-y-auto">
          {panels.map(({ id, label }) => (
            <label
              key={id}
              className="flex items-center gap-2 px-2 py-2 rounded-md hover:bg-muted/60 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={visiblePanels.has(id)}
                onChange={(e) => setPanelVisible(id, e.target.checked)}
                className="rounded border-border"
              />
              <span className="text-sm text-foreground">{label}</span>
            </label>
          ))}
        </div>
        <div className="p-2 border-t border-border">
          <button
            type="button"
            onClick={resetToDefault}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Show all panels
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
