import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  Search,
  Plus,
  Minus,
  Trash2,
  ShoppingCart,
  Send,
  Barcode,
} from "lucide-react";
import { API } from "@/lib/api";

const RequestMaterials = () => {
  const { user } = useAuth();
  const [products, setProducts] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [cart, setCart] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedDept, setSelectedDept] = useState("");
  const [barcodeInput, setBarcodeInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [jobId, setJobId] = useState("");
  const [serviceAddress, setServiceAddress] = useState("");
  const [notes, setNotes] = useState("");
  const barcodeRef = useRef(null);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [search, selectedDept]);

  const extractProducts = (data) => {
    const list = Array.isArray(data) ? data : data?.items ?? [];
    return list.filter((p) => p.quantity > 0);
  };

  const fetchData = async () => {
    try {
      const [deptRes, productsRes] = await Promise.all([
        axios.get(`${API}/departments`),
        axios.get(`${API}/products`),
      ]);
      setDepartments(deptRes.data);
      setProducts(extractProducts(productsRes.data));
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Failed to load catalog");
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (selectedDept) params.append("department_id", selectedDept);
      const response = await axios.get(`${API}/products?${params}`);
      setProducts(extractProducts(response.data));
    } catch (error) {
      console.error("Error fetching products:", error);
    }
  };

  const addToCart = (product) => {
    const existing = cart.find((item) => item.product_id === product.id);
    if (existing) {
      if (existing.quantity >= product.quantity) {
        toast.error("Not enough stock");
        return;
      }
      setCart(
        cart.map((item) =>
          item.product_id === product.id
            ? {
                ...item,
                quantity: item.quantity + 1,
                subtotal: (item.quantity + 1) * item.unit_price,
              }
            : item
        )
      );
    } else {
      setCart([
        ...cart,
        {
          product_id: product.id,
          sku: product.sku,
          name: product.name,
          unit_price: product.price,
          quantity: 1,
          subtotal: product.price,
          max_quantity: product.quantity,
          unit: product.sell_uom || "each",
        },
      ]);
    }
    toast.success(`Added ${product.name}`);
  };

  const handleBarcodeSubmit = async (e) => {
    e?.preventDefault();
    const code = barcodeInput.trim();
    if (!code) return;
    try {
      const res = await axios.get(`${API}/products/by-barcode?barcode=${encodeURIComponent(code)}`);
      const product = res.data;
      if (product && product.quantity > 0) {
        addToCart(product);
        setBarcodeInput("");
        barcodeRef.current?.focus();
      } else {
        toast.error("Product out of stock");
      }
    } catch (err) {
      toast.error("Product not found");
      setBarcodeInput("");
    }
  };

  const updateQuantity = (productId, delta) => {
    setCart(
      cart
        .map((item) => {
          if (item.product_id === productId) {
            const newQty = item.quantity + delta;
            if (newQty <= 0) return null;
            if (newQty > item.max_quantity) {
              toast.error("Not enough stock");
              return item;
            }
            return {
              ...item,
              quantity: newQty,
              subtotal: newQty * item.unit_price,
            };
          }
          return item;
        })
        .filter(Boolean)
    );
  };

  const removeFromCart = (productId) => {
    setCart(cart.filter((item) => item.product_id !== productId));
  };

  const clearCart = () => setCart([]);

  const subtotal = cart.reduce((sum, item) => sum + item.subtotal, 0);

  const openSubmit = () => {
    if (cart.length === 0) {
      toast.error("Cart is empty");
      return;
    }
    setSubmitOpen(true);
  };

  const handleSubmitRequest = async () => {
    setProcessing(true);
    try {
      const payload = {
        items: cart.map(({ product_id, sku, name, quantity, unit_price, subtotal, unit }) => ({
          product_id,
          sku,
          name,
          quantity,
          unit_price,
          cost: 0,
          subtotal,
          unit: unit || "each",
        })),
        job_id: jobId.trim() || null,
        service_address: serviceAddress.trim() || null,
        notes: notes.trim() || null,
      };
      await axios.post(`${API}/material-requests`, payload);
      toast.success("Material request submitted! Staff will process it at pickup.");
      setCart([]);
      setSubmitOpen(false);
      setJobId("");
      setServiceAddress("");
      setNotes("");
      fetchProducts();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit request");
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex items-center gap-3 text-slate-500">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="font-medium">Loading materials…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen" data-testid="request-materials-page">
      {/* Cart Panel */}
      <div className="w-1/3 bg-white border-r border-slate-200 flex flex-col shadow-sm">
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">My Request</h2>
            {cart.length > 0 && (
              <button onClick={clearCart} className="text-sm text-red-600 hover:underline">
                Clear All
              </button>
            )}
          </div>
          {user?.company && (
            <p className="text-sm text-slate-500 mt-1">{user.company}</p>
          )}
        </div>

        <div className="p-4 border-b border-slate-200 bg-slate-50/80">
          <form onSubmit={handleBarcodeSubmit} className="flex gap-2">
            <div className="flex-1 relative">
              <Barcode className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                ref={barcodeRef}
                type="text"
                placeholder="Scan barcode..."
                value={barcodeInput}
                onChange={(e) => setBarcodeInput(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button type="submit" variant="outline" size="sm">
              Add
            </Button>
          </form>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {cart.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <ShoppingCart className="w-14 h-14 mx-auto mb-4 text-slate-300" />
              <p className="font-medium">Cart is empty</p>
              <p className="text-sm mt-1">Search and add materials, or scan barcode</p>
            </div>
          ) : (
            <div className="space-y-3">
              {cart.map((item) => (
                <div
                  key={item.product_id}
                  className="bg-slate-50/80 border border-slate-200 rounded-xl p-4"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-mono text-xs text-slate-500">{item.sku}</p>
                      <p className="font-semibold text-slate-900">{item.name}</p>
                      {item.unit && item.unit !== "each" && (
                        <p className="text-xs text-slate-500 mt-0.5">{item.quantity} {item.unit}</p>
                      )}
                    </div>
                    <button
                      onClick={() => removeFromCart(item.product_id)}
                      className="text-red-500 hover:text-red-700 p-1"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQuantity(item.product_id, -1)}
                        className="w-8 h-8 border border-slate-200 rounded-lg flex items-center justify-center hover:bg-slate-100"
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <input
                        type="number"
                        step="any"
                        min="0.01"
                        max={item.max_quantity}
                        value={item.quantity}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          if (!val || val <= 0) return;
                          if (val > item.max_quantity) { toast.error("Not enough stock"); return; }
                          setCart(cart.map((c) => c.product_id !== item.product_id ? c : { ...c, quantity: val, subtotal: val * c.unit_price }));
                        }}
                        className="w-16 text-center font-mono font-bold border border-slate-200 rounded-lg h-8 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                      <button
                        onClick={() => updateQuantity(item.product_id, 1)}
                        className="w-8 h-8 border border-slate-200 rounded-lg flex items-center justify-center hover:bg-slate-100"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                    <span className="font-mono font-semibold text-amber-600">
                      ${item.subtotal.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-6 border-t border-slate-200 bg-slate-50/80">
          <div className="flex justify-between text-slate-600 mb-4">
            <span>Subtotal</span>
            <span className="font-mono">${subtotal.toFixed(2)}</span>
          </div>
          <Button
            onClick={openSubmit}
            disabled={cart.length === 0}
            className="w-full btn-primary h-14 text-lg"
            data-testid="submit-request-btn"
          >
            <Send className="w-5 h-5 mr-2" />
            Submit Request
          </Button>
        </div>
      </div>

      {/* Products Panel */}
      <div className="flex-1 flex flex-col bg-slate-50/80">
        <div className="p-6 bg-white border-b border-slate-200">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <Input
                type="text"
                placeholder="Search by name, SKU, or barcode..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-12 w-full"
              />
            </div>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="input-workshop px-4 min-w-[200px]"
            >
              <option value="">All Departments</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>{dept.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {products.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <p className="font-medium">No materials found</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {products.map((product) => (
                <div
                  key={product.id}
                  onClick={() => addToCart(product)}
                  className="pos-item cursor-pointer"
                >
                  <div className="aspect-[4/3] bg-slate-100/80 flex items-center justify-center border-b border-slate-200/80">
                    <span className="font-mono text-2xl text-slate-400 font-bold">
                      {product.department_name?.slice(0, 3).toUpperCase() || "---"}
                    </span>
                  </div>
                  <div className="p-4">
                    <p className="font-mono text-xs text-slate-500">{product.sku}</p>
                    <p className="font-semibold text-slate-900 truncate" title={product.name}>
                      {product.name}
                    </p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="font-semibold text-lg text-amber-600">
                        ${product.price.toFixed(2)}
                        <span className="text-xs font-normal text-slate-500 ml-1">/ {product.sell_uom || "each"}</span>
                      </span>
                      <span className="text-xs text-slate-400">{product.quantity} in stock</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Submit Request Dialog */}
      <Dialog open={submitOpen} onOpenChange={setSubmitOpen}>
        <DialogContent className="sm:max-w-lg rounded-2xl">
          <DialogHeader>
            <DialogTitle>Submit material request</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div>
              <Label>Job ID (optional)</Label>
              <Input
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                placeholder="Job or reference number"
                className="mt-2"
              />
            </div>
            <div>
              <Label>Service address (optional)</Label>
              <Input
                value={serviceAddress}
                onChange={(e) => setServiceAddress(e.target.value)}
                placeholder="Pickup or delivery location"
                className="mt-2"
              />
            </div>
            <div>
              <Label>Notes (optional)</Label>
              <Input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional notes..."
                className="mt-2"
              />
            </div>
            <Button
              onClick={handleSubmitRequest}
              disabled={processing}
              className="w-full h-12"
            >
              {processing ? "Submitting…" : "Submit Request"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RequestMaterials;
