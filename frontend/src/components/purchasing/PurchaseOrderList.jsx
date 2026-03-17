import React, { useState, useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Plus, Truck, CheckCircle, BoxIcon, Filter, X, Search } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";

const PO_STATUSES = [
  { value: "", label: "All orders" },
  { value: "ordered", label: "Ordered" },
  { value: "partial", label: "Delivered" },
  { value: "received", label: "Received" },
];

/**
 * Left column: list of purchase orders + new import button.
 *
 * @param {array}    orders          PO list from API
 * @param {string}   selectedId      Currently selected PO ID
 * @param {function} onSelect        (poId: string) => void
 * @param {boolean}  importActive    Whether the import flow is showing
 * @param {function} onNewImport     () => void
 * @param {string}   statusFilter    Current status filter
 * @param {function} onFilterChange  (status: string) => void
 */
export function PurchaseOrderList({
  orders = [],
  selectedId,
  onSelect,
  importActive = false,
  onNewImport,
  statusFilter = "",
  onFilterChange,
}) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return orders;
    const q = search.toLowerCase().trim();
    return orders.filter(
      (po) => po.vendor_name?.toLowerCase().includes(q) || String(po.item_count).includes(q),
    );
  }, [orders, search]);

  return (
    <div className="flex flex-col h-full">
      {/* Header + new import */}
      <div className="px-4 pt-5 pb-3 border-b border-border/50 shrink-0 space-y-3">
        <button
          type="button"
          onClick={onNewImport}
          className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-sm font-medium transition-all ${
            importActive
              ? "border-accent/40 bg-accent/10 text-accent shadow-sm"
              : "border-border/60 bg-card text-foreground hover:border-accent/30 hover:bg-accent/5"
          }`}
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-gradient-from/20 to-accent-gradient-to/20 flex items-center justify-center border border-accent/20 shrink-0">
            <Plus className="w-4 h-4 text-accent" />
          </div>
          Add Order
        </button>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder="Search vendors…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 text-xs pl-8 border-border/50"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-muted-foreground hover:text-foreground"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-3 h-3 text-muted-foreground shrink-0" />
          <Select
            value={statusFilter || "all"}
            onValueChange={(v) => onFilterChange?.(v === "all" ? "" : v)}
          >
            <SelectTrigger className="h-7 text-xs border-border/50 flex-1">
              <SelectValue placeholder="All" />
            </SelectTrigger>
            <SelectContent>
              {PO_STATUSES.map((s) => (
                <SelectItem key={s.value || "all"} value={s.value || "all"}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {statusFilter && (
            <button
              type="button"
              onClick={() => onFilterChange?.("")}
              className="p-1 text-muted-foreground hover:text-foreground"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Order list */}
      <div className="flex-1 overflow-auto">
        {filtered.length === 0 ? (
          <div className="text-center py-12 px-4">
            <Truck className="w-8 h-8 mx-auto text-muted-foreground/40 mb-2" />
            <p className="text-xs text-muted-foreground">
              {search.trim() ? "No matching orders" : "No orders yet"}
            </p>
            {!search.trim() && (
              <p className="text-[10px] text-muted-foreground/60 mt-1">
                Tap &ldquo;Add Order&rdquo; above to get started
              </p>
            )}
          </div>
        ) : (
          <div className="py-1">
            {filtered.map((po) => (
              <button
                key={po.id}
                type="button"
                onClick={() => onSelect(po.id)}
                className={`w-full text-left px-4 py-3 border-b border-border/30 transition-colors ${
                  selectedId === po.id && !importActive
                    ? "bg-accent/8 border-l-2 border-l-accent"
                    : "hover:bg-muted/50 border-l-2 border-l-transparent"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm font-medium text-foreground truncate flex-1">
                    {po.vendor_name}
                  </p>
                  <StatusBadge status={po.status} className="text-[10px] px-1.5 py-0" />
                </div>
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span>
                    {po.item_count} item{po.item_count !== 1 ? "s" : ""}
                  </span>
                  {po.ordered_count > 0 && (
                    <span className="flex items-center gap-0.5">
                      <BoxIcon className="w-2.5 h-2.5" />
                      {po.ordered_count}
                    </span>
                  )}
                  {po.pending_count > 0 && (
                    <span className="flex items-center gap-0.5 text-accent">
                      <Truck className="w-2.5 h-2.5" />
                      {po.pending_count}
                    </span>
                  )}
                  {po.arrived_count > 0 && (
                    <span className="flex items-center gap-0.5 text-success">
                      <CheckCircle className="w-2.5 h-2.5" />
                      {po.arrived_count}
                    </span>
                  )}
                  <span className="ml-auto">{new Date(po.created_at).toLocaleDateString()}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
