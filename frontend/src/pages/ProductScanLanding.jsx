import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Loader2, Package, AlertCircle, ShoppingCart, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { ROLES } from "@/lib/constants";
import api from "@/lib/api-client";

/**
 * Landing page for QR code deep links: /product/scan/:code
 *
 * When an iPad user scans a printed QR label with the native camera,
 * Safari opens this URL. The page resolves the product and offers:
 *  - Contractors: "Add to cart" (redirects to /scan with the code pre-loaded)
 *  - Admins: "View product" (redirects to /inventory with detail open)
 *  - Not found: helpful message with a link to search inventory
 */
const ProductScanLanding = () => {
  const { code } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!code) {
      setError("No product code provided");
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const p = await api.products.byBarcode(decodeURIComponent(code));
        if (!cancelled) setProduct(p);
      } catch {
        if (!cancelled) setError("Product not found");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code]);

  if (loading) {
    return (
      <div
        className="min-h-[60vh] flex flex-col items-center justify-center gap-4"
        data-testid="product-scan-landing"
      >
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Looking up product…</p>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div
        className="min-h-[60vh] flex flex-col items-center justify-center gap-4 px-6 text-center"
        data-testid="product-scan-landing"
      >
        <div className="w-14 h-14 rounded-2xl bg-destructive/10 flex items-center justify-center">
          <AlertCircle className="w-7 h-7 text-destructive" />
        </div>
        <h2 className="text-lg font-semibold">{error || "Product not found"}</h2>
        <p className="text-sm text-muted-foreground max-w-xs">
          The scanned code &quot;{decodeURIComponent(code)}&quot; didn&apos;t match any product.
        </p>
        <div className="flex gap-2 mt-2">
          <Button variant="outline" onClick={() => navigate("/inventory")}>
            Search inventory
          </Button>
          <Button variant="outline" onClick={() => navigate("/")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Home
          </Button>
        </div>
      </div>
    );
  }

  const isContractor = user?.role === ROLES.CONTRACTOR;

  return (
    <div
      className="min-h-[60vh] flex flex-col items-center justify-center gap-6 px-6 text-center"
      data-testid="product-scan-landing"
    >
      <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center">
        <Package className="w-7 h-7 text-accent" />
      </div>
      <div>
        <h2 className="text-xl font-semibold">{product.name}</h2>
        <p className="font-mono text-sm text-muted-foreground mt-1">{product.sku}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 text-center w-full max-w-xs">
        <div className="bg-muted rounded-xl p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Price</p>
          <p className="font-mono font-semibold text-lg">${(product.price || 0).toFixed(2)}</p>
        </div>
        <div className="bg-muted rounded-xl p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">In Stock</p>
          <p className="font-mono font-semibold text-lg">
            {product.sell_quantity ?? product.quantity ?? 0}
          </p>
        </div>
      </div>

      <div className="flex gap-2 mt-2">
        {isContractor ? (
          <Button
            onClick={() => navigate(`/scan?add=${encodeURIComponent(product.sku)}`)}
            className="btn-primary h-12 px-8"
          >
            <ShoppingCart className="w-5 h-5 mr-2" />
            Add to Cart
          </Button>
        ) : (
          <Button
            onClick={() => navigate(`/inventory?highlight=${encodeURIComponent(product.id)}`)}
            className="btn-primary h-12 px-8"
          >
            <Package className="w-5 h-5 mr-2" />
            View in Inventory
          </Button>
        )}
        <Button variant="outline" className="h-12" onClick={() => navigate("/")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Home
        </Button>
      </div>
    </div>
  );
};

export default ProductScanLanding;
