import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export function ReportDetailModal({
  open,
  onClose,
  title,
  subtitle,
  controls,
  children,
  className,
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent
        className={cn("max-w-[900px] w-[95vw] max-h-[90vh] overflow-y-auto p-0", className)}
      >
        <div className="sticky top-0 z-10 bg-surface border-b border-border/60 px-7 pt-6 pb-4">
          <DialogHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <DialogTitle className="text-lg font-semibold text-foreground">{title}</DialogTitle>
                {subtitle && (
                  <DialogDescription className="text-sm text-muted-foreground mt-1">
                    {subtitle}
                  </DialogDescription>
                )}
              </div>
              {controls && <div className="shrink-0 flex items-center gap-2">{controls}</div>}
            </div>
          </DialogHeader>
        </div>
        <div className="px-7 py-6 space-y-6">{children}</div>
      </DialogContent>
    </Dialog>
  );
}

export function Narrative({ items = [] }) {
  if (!items.length) return null;
  return (
    <div className="bg-muted/40 rounded-xl border border-border/50 p-4 space-y-2">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-2">
        Key Insights
      </p>
      {items.map((item, i) => (
        <p key={i} className="flex items-start gap-2 text-sm text-muted-foreground leading-relaxed">
          <span className="text-accent mt-0.5 shrink-0">&bull;</span>
          <span>{item}</span>
        </p>
      ))}
    </div>
  );
}
