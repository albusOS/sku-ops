import { Link } from "react-router-dom";
import { ShoppingCart, ScanBarcode } from "lucide-react";

export function IssueMaterialsCTA() {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Link
        to="/pos"
        className="inline-flex items-center gap-2 rounded-xl border border-border/80 bg-surface px-4 py-3 shadow-soft hover:border-accent/40 hover:bg-accent/5 transition-all text-foreground"
      >
        <div className="w-9 h-9 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
          <ShoppingCart className="w-4 h-4 text-accent" />
        </div>
        <div className="text-left">
          <p className="font-semibold text-sm">Issue materials</p>
          <p className="text-xs text-muted-foreground">
            Add items and create a withdrawal (no request)
          </p>
        </div>
      </Link>
      <Link
        to="/scan"
        className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-surface/80 px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:border-border transition-all"
      >
        <ScanBarcode className="w-4 h-4 shrink-0" />
        Scan mode
      </Link>
    </div>
  );
}
