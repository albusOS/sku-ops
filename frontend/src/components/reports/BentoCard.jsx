import { cn } from "@/lib/utils";
import { Expand } from "lucide-react";

const SIZE_CLASSES = {
  medium: "col-span-1 md:col-span-1 xl:col-span-2",
  large: "col-span-1 md:col-span-2 xl:col-span-2",
};

const STATUS_STYLES = {
  danger: {
    bar: "before:from-destructive/80 before:via-destructive/40 before:to-transparent",
    border: "border-destructive/25",
    glow: "shadow-[0_0_16px_-4px_rgb(220_38_38/0.18)]",
  },
  warn: {
    bar: "before:from-warning/80 before:via-warning/40 before:to-transparent",
    border: "border-warning/25",
    glow: "shadow-[0_0_16px_-4px_rgb(245_158_11/0.15)]",
  },
  healthy: {
    bar: "before:from-success/70 before:via-success/30 before:to-transparent",
    border: "border-success/20",
    glow: "",
  },
};

export function BentoCard({
  title,
  metric,
  insight,
  size = "medium",
  status,
  onClick,
  children,
  className,
}) {
  const isLoading = metric === "—" || metric === undefined;
  const s = status && STATUS_STYLES[status];

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group relative bg-card/70 rounded-2xl border border-border/70 shadow-soft p-6 md:p-7 backdrop-blur-sm overflow-hidden transition-all text-left w-full grain",
        "hover:shadow-md hover:border-accent/40 hover:scale-[1.005] active:scale-[0.998]",
        "before:absolute before:inset-x-0 before:top-0 before:h-[2px] before:bg-gradient-to-r",
        s
          ? cn(s.bar, s.border, s.glow)
          : "before:from-accent/80 before:via-category-4/60 before:to-transparent",
        SIZE_CLASSES[size],
        className,
      )}
    >
      <div className="relative">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h3 className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground mb-2">
              {title}
            </h3>
            {isLoading ? (
              <div className="h-7 w-24 rounded-md bg-muted/60 animate-shimmer" />
            ) : (
              <p className="text-2xl font-bold text-foreground tabular-nums leading-none animate-metric">
                {metric}
              </p>
            )}
          </div>
          <div className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center bg-muted/60 text-muted-foreground/50 opacity-0 group-hover:opacity-100 transition-opacity">
            <Expand className="w-3.5 h-3.5" />
          </div>
        </div>

        <div className="min-h-[80px]">{children}</div>

        {insight && (
          <p className="mt-4 text-xs text-muted-foreground leading-relaxed border-t border-border/50 pt-3">
            {insight}
          </p>
        )}
      </div>
    </button>
  );
}
