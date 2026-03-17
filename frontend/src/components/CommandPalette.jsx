import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  LayoutDashboard,
  Package,
  ShoppingCart,
  Truck,
  BarChart3,
  Settings,
  Layers,
  HardHat,
  ClipboardCheck,
  ScanBarcode,
  History,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from "@/components/ui/command";
import api from "@/lib/api-client";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard, section: "Pages" },
  { label: "Point of Sale", path: "/pos", icon: ShoppingCart, section: "Operations" },
  { label: "Direct Issue", path: "/pos/issue", icon: ShoppingCart, section: "Operations" },
  { label: "Scan Mode", path: "/pos/scan", icon: ScanBarcode, section: "Operations" },
  {
    label: "Request Materials",
    path: "/request-materials",
    icon: ShoppingCart,
    section: "Operations",
  },
  { label: "My History", path: "/my-history", icon: History, section: "Operations" },
  { label: "Contractors", path: "/contractors", icon: HardHat, section: "Operations" },
  { label: "Jobs", path: "/jobs", icon: ClipboardCheck, section: "Operations" },
  { label: "Purchasing", path: "/purchasing", icon: Truck, section: "Purchasing" },
  { label: "Vendors", path: "/vendors", icon: Truck, section: "Purchasing" },
  { label: "Products", path: "/inventory", icon: Package, section: "Inventory" },
  { label: "Categories", path: "/departments", icon: Layers, section: "Inventory" },
  { label: "Stock Counts", path: "/cycle-counts", icon: ClipboardCheck, section: "Inventory" },
  { label: "Reports", path: "/reports", icon: BarChart3, section: "Pages" },
  { label: "Xero Status", path: "/xero-health", icon: ShieldCheck, section: "Pages" },
  { label: "Settings", path: "/settings", icon: Settings, section: "Pages" },
];

export function CommandPalette({ open, onOpenChange }) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [products, setProducts] = useState([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const searchTimer = useRef(null);

  useEffect(() => {
    if (!open) {
      setSearch("");
      setProducts([]);
    }
  }, [open]);

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!search.trim() || search.trim().length < 2) {
      setProducts([]);
      setLoadingProducts(false);
      return;
    }
    setLoadingProducts(true);
    searchTimer.current = setTimeout(async () => {
      try {
        const res = await api.products.list({ search: search.trim(), limit: 8 });
        const items = Array.isArray(res) ? res : res.items || [];
        setProducts(items);
      } catch {
        setProducts([]);
      } finally {
        setLoadingProducts(false);
      }
    }, 250);
    return () => clearTimeout(searchTimer.current);
  }, [search]);

  const handleSelect = useCallback(
    (path) => {
      onOpenChange(false);
      navigate(path);
    },
    [navigate, onOpenChange],
  );

  const grouped = NAV_ITEMS.reduce((acc, item) => {
    if (!acc[item.section]) acc[item.section] = [];
    acc[item.section].push(item);
    return acc;
  }, {});

  const showProducts = search.trim().length >= 2;

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={() => onOpenChange(false)}
          />

          {/* Palette */}
          <motion.div
            key="palette"
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ type: "spring", stiffness: 400, damping: 36 }}
            className="fixed left-1/2 top-[20vh] z-50 w-full max-w-xl -translate-x-1/2"
            style={{ maxHeight: "60vh" }}
          >
            <Command
              className="rounded-2xl border border-border/80 bg-popover shadow-2xl overflow-hidden"
              shouldFilter={!showProducts}
            >
              <div className="flex items-center border-b border-border/60 px-4">
                <Search className="mr-3 h-4 w-4 shrink-0 text-muted-foreground" />
                <CommandInput
                  placeholder="Search products, go to page…"
                  value={search}
                  onValueChange={setSearch}
                  className="h-12 border-0 bg-transparent text-sm focus:ring-0 focus-visible:ring-0 pl-0"
                  style={{ boxShadow: "none" }}
                />
                {loadingProducts && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground ml-2 shrink-0" />
                )}
                <kbd className="hidden sm:flex items-center gap-1 rounded border border-border/60 bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground font-mono ml-2">
                  ESC
                </kbd>
              </div>

              <CommandList className="max-h-[calc(60vh-3rem)] overflow-y-auto py-2">
                <CommandEmpty className="py-8 text-center text-sm text-muted-foreground">
                  {loadingProducts ? "Searching…" : `No results for \u201c${search}\u201d`}
                </CommandEmpty>

                {showProducts && products.length > 0 && (
                  <>
                    <CommandGroup
                      heading="Products"
                      className="[&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2"
                    >
                      {products.map((p) => (
                        <CommandItem
                          key={p.id}
                          value={`product-${p.name}-${p.sku || ""}`}
                          onSelect={() => handleSelect(`/inventory?product=${p.id}`)}
                          className="mx-1 rounded-lg px-3 py-2 cursor-pointer data-[selected=true]:bg-accent/15 data-[selected=true]:text-foreground"
                        >
                          <Package className="h-4 w-4 text-muted-foreground shrink-0" />
                          <div className="ml-2 min-w-0 flex-1">
                            <span className="text-sm truncate block">{p.name}</span>
                            <span className="text-[10px] text-muted-foreground">
                              {p.sku && <span className="font-mono">{p.sku}</span>}
                              {p.department_name && (
                                <span>
                                  {p.sku ? " · " : ""}
                                  {p.department_name}
                                </span>
                              )}
                              {p.qty_on_hand != null && (
                                <span>
                                  {" · "}
                                  {p.qty_on_hand} in stock
                                </span>
                              )}
                            </span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    <CommandSeparator className="my-1" />
                  </>
                )}

                {Object.entries(grouped).map(([section, items]) => (
                  <CommandGroup
                    key={section}
                    heading={section}
                    className="[&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2"
                  >
                    {items.map((item) => (
                      <CommandItem
                        key={item.path}
                        value={item.label}
                        onSelect={() => handleSelect(item.path)}
                        className="mx-1 rounded-lg px-3 py-2 cursor-pointer data-[selected=true]:bg-accent/15 data-[selected=true]:text-foreground"
                      >
                        <item.icon className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="ml-2 text-sm">{item.label}</span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                ))}
              </CommandList>

              <div className="border-t border-border/40 px-4 py-2 flex items-center gap-4 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <kbd className="rounded border border-border/60 bg-muted px-1 py-0.5 font-mono">
                    ↑↓
                  </kbd>{" "}
                  navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="rounded border border-border/60 bg-muted px-1 py-0.5 font-mono">
                    ↵
                  </kbd>{" "}
                  go
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="rounded border border-border/60 bg-muted px-1 py-0.5 font-mono">
                    esc
                  </kbd>{" "}
                  close
                </span>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
