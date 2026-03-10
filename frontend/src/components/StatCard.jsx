import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

const ACCENTS = {
  amber: { bar: "bg-category-1", icon: "bg-category-1/10 text-category-1" },
  emerald: { bar: "bg-category-2", icon: "bg-category-2/10 text-category-2" },
  blue: { bar: "bg-category-3", icon: "bg-category-3/10 text-category-3" },
  orange: { bar: "bg-category-5", icon: "bg-category-5/10 text-category-5" },
  violet: { bar: "bg-category-4", icon: "bg-category-4/10 text-category-4" },
  rose: { bar: "bg-destructive", icon: "bg-destructive/10 text-destructive" },
  slate: { bar: "bg-muted", icon: "bg-muted text-muted-foreground" },
};

export function StatCard({ label, value, note, icon: Icon, accent = "slate", className, href }) {
  const cfg = ACCENTS[accent] || ACCENTS.slate;
  const Wrapper = href ? Link : "div";
  const wrapperProps = href ? { to: href } : {};

  return (
    <Wrapper
      {...wrapperProps}
      className={cn(
        "bg-surface rounded-xl border border-border/80 p-5 relative overflow-hidden shadow-soft block",
        href && "hover:border-accent/40 hover:shadow-md transition-all cursor-pointer",
        className,
      )}
    >
      <div className={cn("absolute top-0 left-0 right-0 h-[2px]", cfg.bar)} />
      <div className="flex items-start justify-between mb-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </p>
        {Icon && (
          <div
            className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center ring-1 ring-border/60",
              cfg.icon,
            )}
          >
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-foreground tabular-nums leading-none">{value}</p>
      {note && <p className="text-xs text-muted-foreground mt-2">{note}</p>}
    </Wrapper>
  );
}
