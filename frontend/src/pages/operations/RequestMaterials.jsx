import { useState, useEffect, useMemo, useRef } from "react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Trash2,
  ShoppingCart,
  Send,
  Barcode,
  Package,
  X,
  Plus,
  Minus,
  ChevronRight,
} from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { QuantityControl } from "@/components/QuantityControl";
import { useProducts } from "@/hooks/useProducts";
import { useDepartments } from "@/hooks/useDepartments";
import { useCreateMaterialRequest } from "@/hooks/useMaterialRequests";
import { useCart } from "@/hooks/useCart";
import { useBarcodeScanner } from "@/hooks/useBarcodeScanner";
import { UnknownBarcodeSheet } from "@/components/UnknownBarcodeSheet";
import { getErrorMessage } from "@/lib/api-client";
import { SubmitRequestModal } from "./_SubmitRequestModal";

const RequestMaterials = () => {
  const { user } = useAuth();
  const searchRef = useRef(null);

  const {
    items: cart,
    addItem: addToCart,
    updateQuantity,
    removeItem,
    clear: clearCart,
    syncStock,
    total: subtotal,
  } = useCart();
  const [search, setSearch] = useState("");
  const [selectedDept, setSelectedDept] = useState("all");
  const [submitOpen, setSubmitOpen] = useState(false);
  const [unknownBarcode, setUnknownBarcode] = useState(null);
  const [jobId, setJobId] = useState("");
  const [serviceAddress, setServiceAddress] = useState("");
  const [notes, setNotes] = useState("");

  const productParams = {
    search: search || undefined,
    category_id: selectedDept !== "all" ? selectedDept : undefined,
  };
  const {
    data: productsData,
    isLoading: productsLoading,
    isError: productsError,
    error: productsErr,
    refetch: refetchProducts,
  } = useProducts(productParams);
  const { data: allProductsData } = useProducts();
  const {
    data: departmentsData,
    isLoading: deptsLoading,
    isError: deptsError,
    error: deptsErr,
    refetch: refetchDepts,
  } = useDepartments();
  const createRequest = useCreateMaterialRequest();

  const departments = departmentsData || [];
  const rawProducts = Array.isArray(productsData) ? productsData : productsData?.items || [];
  const products = rawProducts.filter((p) => (p.sell_quantity ?? p.quantity) > 0);
  const allProducts = useMemo(
    () => (Array.isArray(allProductsData) ? allProductsData : allProductsData?.items || []),
    [allProductsData],
  );

  useEffect(() => {
    syncStock(allProducts);
  }, [allProducts, syncStock]);

  const scanner = useBarcodeScanner({
    onSuccess: (product) => {
      if ((product.sell_quantity ?? product.quantity) <= 0) {
        toast.error("Product out of stock");
        return;
      }
      addToCart(product);
      toast.success(`Added: ${product.sku} (+1)`);
    },
    onNotFound: ({ barcode }) => setUnknownBarcode(barcode),
    onInvalidCheckDigit: (barcode) => toast.error(`Invalid barcode — bad check digit (${barcode})`),
  });

  const handleSubmitRequest = async () => {
    try {
      await createRequest.mutateAsync({
        items: cart.map(({ product_id, sku, name, quantity, unit_price, unit }) => ({
          product_id,
          sku,
          name,
          quantity,
          unit_price,
          cost: 0,
          subtotal: quantity * unit_price,
          unit: unit || "each",
        })),
        job_id: jobId.trim() || null,
        service_address: serviceAddress.trim() || null,
        notes: notes.trim() || null,
      });
      toast.success("Material request submitted!");
      clearCart();
      setSubmitOpen(false);
      setJobId("");
      setServiceAddress("");
      setNotes("");
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  const cartItemCount = cart.reduce((sum, item) => sum + item.quantity, 0);
  const cartInProduct = (productId) => cart.find((i) => i.product_id === productId);

  if (productsLoading && deptsLoading) return <PageSkeleton />;
  if (productsError) return <QueryError error={productsErr} onRetry={refetchProducts} />;
  if (deptsError) return <QueryError error={deptsErr} onRetry={refetchDepts} />;

  return (
    <div className="flex h-screen" data-testid="request-materials-page">
      {/* ── Catalog area ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Search header */}
        <div className="flex-shrink-0 bg-card border-b border-border px-5 pt-5 pb-4">
          <div className="max-w-4xl">
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-lg font-semibold text-foreground tracking-tight">Materials</h1>
              {user?.company && (
                <span className="text-xs text-muted-foreground">· {user.company}</span>
              )}
            </div>

            {/* Search bar */}
            <div className="relative mt-3">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
              <Input
                ref={searchRef}
                type="text"
                placeholder="Search by name, SKU, or barcode…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-11 h-11 text-sm bg-muted/50 border-border/80 focus:bg-card"
              />
              {search && (
                <button
                  onClick={() => {
                    setSearch("");
                    searchRef.current?.focus();
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground rounded-md"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Category chips */}
            <div className="flex items-center gap-2 mt-3 overflow-x-auto pb-1 scrollbar-none">
              <button
                onClick={() => setSelectedDept("all")}
                className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  selectedDept === "all"
                    ? "bg-accent text-accent-foreground shadow-sm"
                    : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                }`}
              >
                All
              </button>
              {departments.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setSelectedDept(d.id === selectedDept ? "all" : d.id)}
                  className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    selectedDept === d.id
                      ? "bg-accent text-accent-foreground shadow-sm"
                      : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                  }`}
                >
                  {d.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Product grid */}
        <div className="flex-1 overflow-auto p-5">
          {products.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-4">
                <Package className="w-7 h-7 text-muted-foreground" />
              </div>
              <p className="font-medium text-foreground">No materials found</p>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                {search
                  ? `No results for "${search}". Try a different search term.`
                  : "No products available in this category."}
              </p>
              {search && (
                <Button variant="outline" size="sm" onClick={() => setSearch("")} className="mt-4">
                  Clear search
                </Button>
              )}
            </div>
          ) : (
            <>
              <p className="text-xs text-muted-foreground mb-3">
                {products.length} product{products.length !== 1 ? "s" : ""} available
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
                {products.map((product) => {
                  const inCart = cartInProduct(product.id);
                  const available = Math.floor(product.sell_quantity ?? product.quantity);
                  return (
                    <div
                      key={product.id}
                      className={`group relative bg-card border rounded-xl overflow-hidden transition-all hover:shadow-md ${
                        inCart
                          ? "border-accent/40 shadow-sm ring-1 ring-accent/10"
                          : "border-border/80 hover:border-border"
                      }`}
                    >
                      {/* Category badge */}
                      <div className="aspect-[4/3] bg-gradient-to-br from-muted to-muted/60 flex items-center justify-center relative">
                        <span className="font-mono text-2xl font-bold text-muted-foreground/30 select-none">
                          {product.category_name?.slice(0, 3).toUpperCase() || "---"}
                        </span>
                        {product.category_name && (
                          <span className="absolute top-2 left-2 text-[9px] font-medium text-muted-foreground bg-card/80 backdrop-blur-sm px-2 py-0.5 rounded-full border border-border/50">
                            {product.category_name}
                          </span>
                        )}
                        {inCart && (
                          <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-accent text-accent-foreground flex items-center justify-center text-[10px] font-bold shadow-sm">
                            {inCart.quantity}
                          </div>
                        )}
                        <span className="absolute bottom-2 right-2 text-[10px] text-muted-foreground/70 bg-card/80 backdrop-blur-sm px-2 py-0.5 rounded-full border border-border/50 tabular-nums">
                          {available} avail
                        </span>
                      </div>
                      <div className="p-3">
                        <p className="font-mono text-[10px] text-muted-foreground leading-none">
                          {product.sku}
                        </p>
                        <p className="text-sm font-medium text-foreground truncate mt-1">
                          {product.name}
                        </p>
                        <div className="flex items-center justify-between mt-2.5">
                          <span className="font-semibold text-foreground tabular-nums">
                            ${(product.sell_price ?? product.price).toFixed(2)}
                            <span className="text-[10px] font-normal text-muted-foreground ml-0.5">
                              /{product.sell_uom || "ea"}
                            </span>
                          </span>
                          {inCart ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() =>
                                  inCart.quantity <= 1
                                    ? removeItem(product.id)
                                    : updateQuantity(product.id, inCart.quantity - 1)
                                }
                                className="w-7 h-7 rounded-lg bg-muted hover:bg-muted/80 flex items-center justify-center text-foreground transition-colors"
                              >
                                {inCart.quantity <= 1 ? (
                                  <Trash2 className="w-3 h-3 text-destructive" />
                                ) : (
                                  <Minus className="w-3 h-3" />
                                )}
                              </button>
                              <span className="w-7 text-center text-xs font-semibold tabular-nums">
                                {inCart.quantity}
                              </span>
                              <button
                                onClick={() => updateQuantity(product.id, inCart.quantity + 1)}
                                disabled={inCart.quantity >= available}
                                className="w-7 h-7 rounded-lg bg-accent/10 hover:bg-accent/20 flex items-center justify-center text-accent transition-colors disabled:opacity-40"
                              >
                                <Plus className="w-3 h-3" />
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => addToCart(product)}
                              className="h-7 px-2.5 rounded-lg bg-accent/10 hover:bg-accent/20 text-accent text-xs font-medium transition-colors flex items-center gap-1"
                            >
                              <Plus className="w-3 h-3" />
                              Add
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Cart sidebar ── */}
      <div className="w-80 xl:w-96 bg-card border-l border-border flex flex-col shadow-sm shrink-0">
        {/* Cart header */}
        <div className="p-5 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShoppingCart className="w-4 h-4 text-foreground" />
              <h2 className="text-base font-semibold text-foreground">My Request</h2>
              {cartItemCount > 0 && (
                <Badge variant="secondary" className="text-[10px] px-1.5 h-5">
                  {cartItemCount}
                </Badge>
              )}
            </div>
            {cart.length > 0 && (
              <button
                onClick={clearCart}
                className="text-xs text-destructive/70 hover:text-destructive transition-colors"
              >
                Clear all
              </button>
            )}
          </div>
        </div>

        {/* Barcode scanner */}
        <div className="px-4 py-3 border-b border-border bg-muted/50">
          <div className="relative">
            <Barcode className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input
              ref={scanner.inputRef}
              type="text"
              placeholder="Scan barcode…"
              value={scanner.value}
              onChange={(e) => scanner.setValue(e.target.value)}
              onKeyDown={scanner.onKeyDown}
              className="pl-10 h-9 text-sm bg-card"
              disabled={scanner.scanning}
            />
          </div>
        </div>

        {/* Cart items */}
        <div className="flex-1 overflow-auto p-4">
          {cart.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
                <ShoppingCart className="w-6 h-6 text-muted-foreground/40" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">Cart is empty</p>
              <p className="text-xs text-muted-foreground/70 mt-1">Browse or scan to add items</p>
            </div>
          ) : (
            <div className="space-y-2">
              {cart.map((item) => (
                <div
                  key={item.product_id}
                  className="bg-muted/60 border border-border/60 rounded-xl p-3 transition-colors hover:bg-muted/80"
                >
                  <div className="flex justify-between items-start gap-2 mb-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-[10px] text-muted-foreground">{item.sku}</p>
                      <p className="text-sm font-medium text-foreground truncate">{item.name}</p>
                    </div>
                    <button
                      onClick={() => removeItem(item.product_id)}
                      className="text-muted-foreground/50 hover:text-destructive p-1 rounded-md transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <QuantityControl
                      value={item.quantity}
                      onChange={(v) => updateQuantity(item.product_id, v)}
                      max={item.max_quantity}
                    />
                    <span className="font-semibold text-sm text-foreground tabular-nums">
                      ${(item.quantity * item.unit_price).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cart footer */}
        <div className="p-4 border-t border-border bg-card">
          {cart.length > 0 && (
            <div className="space-y-1.5 mb-4">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>
                  {cartItemCount} item{cartItemCount !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Subtotal</span>
                <span className="font-bold font-mono text-foreground tabular-nums">
                  ${subtotal.toFixed(2)}
                </span>
              </div>
            </div>
          )}
          <Button
            onClick={() => (cart.length > 0 ? setSubmitOpen(true) : toast.error("Cart is empty"))}
            disabled={cart.length === 0}
            className="w-full btn-primary h-11 text-sm font-semibold"
            data-testid="submit-request-btn"
          >
            <Send className="w-4 h-4 mr-2" />
            Submit Request
            {cart.length > 0 && <ChevronRight className="w-4 h-4 ml-auto" />}
          </Button>
        </div>
      </div>

      <SubmitRequestModal
        open={submitOpen}
        onOpenChange={setSubmitOpen}
        jobId={jobId}
        onJobIdChange={setJobId}
        serviceAddress={serviceAddress}
        onServiceAddressChange={setServiceAddress}
        notes={notes}
        onNotesChange={setNotes}
        onSubmit={handleSubmitRequest}
        isPending={createRequest.isPending}
      />

      <UnknownBarcodeSheet
        open={!!unknownBarcode}
        onOpenChange={(open) => {
          if (!open) setUnknownBarcode(null);
        }}
        barcode={unknownBarcode}
        products={allProducts}
        onAddProduct={(product) => {
          addToCart(product);
          toast.success(`Added: ${product.sku} (+1)`);
          setUnknownBarcode(null);
        }}
      />
    </div>
  );
};

export default RequestMaterials;
