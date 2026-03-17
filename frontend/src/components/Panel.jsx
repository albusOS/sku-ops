import { cn } from "@/lib/utils";

const SEVERITY_STYLES = {
  danger:
    "border-destructive/30 bg-destructive/[0.03] shadow-[inset_0_1px_0_0_rgb(220_38_38/0.08),0_0_12px_-3px_rgb(220_38_38/0.15)]",
  warn: "border-warning/30 bg-warning/[0.03] shadow-[inset_0_1px_0_0_rgb(245_158_11/0.08),0_0_12px_-3px_rgb(245_158_11/0.12)]",
  success: "border-success/30 bg-success/[0.03] shadow-[inset_0_1px_0_0_rgb(16_185_129/0.08)]",
};

export function Panel({ children, className, grain = false, severity }) {
  return (
    <div
      className={cn(
        "bg-surface rounded-xl border border-border/80 shadow-soft p-6 relative",
        grain && "grain",
        severity && SEVERITY_STYLES[severity],
        className,
      )}
    >
      {children}
    </div>
  );
}

/** Section heading with optional right-aligned action and icon.
 *  variant="default" (subtle label) | "report" (bold uppercase with accent left border)
 */
export function SectionHead({ title, action, icon: Icon, variant = "default" }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {Icon && (
          <Icon
            className={cn(
              "w-4 h-4 shrink-0",
              variant === "report" ? "text-accent" : "text-muted-foreground/60",
            )}
          />
        )}
        {variant === "report" ? (
          <h3 className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground border-l-2 border-accent pl-3">
            {title}
          </h3>
        ) : (
          <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        )}
      </div>
      {action}
    </div>
  );
}
