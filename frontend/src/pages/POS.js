import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
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
  CreditCard,
  Banknote,
  ShoppingCart,
  Check,
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const POS = () => {
  const [products, setProducts] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [cart, setCart] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedDept, setSelectedDept] = useState("");
  const [loading, setLoading] = useState(true);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [search, selectedDept]);

  const fetchData = async () => {
    try {
      const [deptRes] = await Promise.all([
        axios.get(`${API}/departments`),
      ]);
      setDepartments(deptRes.data);
      await fetchProducts();
    } catch (error) {
      console.error("Error fetching data:", error);
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
      setProducts(response.data.filter(p => p.quantity > 0));
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
                subtotal: (item.quantity + 1) * item.price,
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
          price: product.price,
          quantity: 1,
          subtotal: product.price,
          max_quantity: product.quantity,
        },
      ]);
    }
    toast.success(`Added ${product.name}`);
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
              subtotal: newQty * item.price,
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

  const clearCart = () => {
    setCart([]);
  };

  const subtotal = cart.reduce((sum, item) => sum + item.subtotal, 0);
  const tax = subtotal * 0.08;
  const total = subtotal + tax;

  const handleCheckout = async () => {
    if (cart.length === 0) {
      toast.error("Cart is empty");
      return;
    }

    setProcessing(true);
    try {
      const saleData = {
        items: cart.map(({ product_id, sku, name, quantity, price, subtotal }) => ({
          product_id,
          sku,
          name,
          quantity,
          price,
          subtotal,
        })),
        payment_method: paymentMethod,
      };

      await axios.post(`${API}/sales`, saleData);
      toast.success("Sale completed!");
      setCart([]);
      setCheckoutOpen(false);
      fetchProducts();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Checkout failed");
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-slate-600 font-heading text-xl uppercase tracking-wider">
          Loading POS...
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen" data-testid="pos-page">
      {/* Cart Panel - Left Side */}
      <div className="w-1/3 bg-white border-r-2 border-slate-200 flex flex-col" data-testid="cart-panel">
        {/* Cart Header */}
        <div className="p-6 border-b-2 border-slate-200">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-bold text-xl text-slate-900 uppercase tracking-wider">
              Current Order
            </h2>
            {cart.length > 0 && (
              <button
                onClick={clearCart}
                className="text-sm text-red-600 hover:underline"
                data-testid="clear-cart-btn"
              >
                Clear All
              </button>
            )}
          </div>
        </div>

        {/* Cart Items */}
        <div className="flex-1 overflow-auto p-4" data-testid="cart-items">
          {cart.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <ShoppingCart className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="font-medium">Cart is empty</p>
              <p className="text-sm">Add products to start a sale</p>
            </div>
          ) : (
            <div className="space-y-3">
              {cart.map((item) => (
                <div
                  key={item.product_id}
                  className="bg-slate-50 border-2 border-slate-200 rounded-sm p-4"
                  data-testid={`cart-item-${item.sku}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-mono text-xs text-slate-500">{item.sku}</p>
                      <p className="font-semibold text-slate-900">{item.name}</p>
                    </div>
                    <button
                      onClick={() => removeFromCart(item.product_id)}
                      className="text-red-500 hover:text-red-700 p-1"
                      data-testid={`remove-item-${item.sku}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQuantity(item.product_id, -1)}
                        className="w-8 h-8 border-2 border-slate-300 rounded-sm flex items-center justify-center hover:bg-slate-100"
                        data-testid={`qty-minus-${item.sku}`}
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <span className="w-10 text-center font-mono font-bold">
                        {item.quantity}
                      </span>
                      <button
                        onClick={() => updateQuantity(item.product_id, 1)}
                        className="w-8 h-8 border-2 border-slate-300 rounded-sm flex items-center justify-center hover:bg-slate-100"
                        data-testid={`qty-plus-${item.sku}`}
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="font-heading font-bold text-lg">
                      ${item.subtotal.toFixed(2)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cart Summary */}
        <div className="p-6 border-t-2 border-slate-200 bg-slate-50">
          <div className="space-y-2 mb-4">
            <div className="flex justify-between text-slate-600">
              <span>Subtotal</span>
              <span className="font-mono">${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Tax (8%)</span>
              <span className="font-mono">${tax.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xl font-bold text-slate-900 pt-2 border-t border-slate-300">
              <span className="font-heading uppercase">Total</span>
              <span className="font-mono">${total.toFixed(2)}</span>
            </div>
          </div>
          <Button
            onClick={() => setCheckoutOpen(true)}
            disabled={cart.length === 0}
            className="w-full btn-primary h-14 text-lg"
            data-testid="checkout-btn"
          >
            <CreditCard className="w-5 h-5 mr-2" />
            Checkout
          </Button>
        </div>
      </div>

      {/* Products Panel - Right Side */}
      <div className="flex-1 flex flex-col bg-slate-50" data-testid="products-panel">
        {/* Search & Filter Bar */}
        <div className="p-6 bg-white border-b-2 border-slate-200">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <Input
                type="text"
                placeholder="Search products by name, SKU, or barcode..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input-workshop pl-12 w-full"
                data-testid="pos-search-input"
              />
            </div>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="input-workshop px-4 min-w-[200px]"
              data-testid="pos-department-filter"
            >
              <option value="">All Departments</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Products Grid */}
        <div className="flex-1 overflow-auto p-6" data-testid="products-grid">
          {products.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <p className="font-medium">No products found</p>
              <p className="text-sm">Add products in Inventory to see them here</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {products.map((product) => (
                <div
                  key={product.id}
                  onClick={() => addToCart(product)}
                  className="pos-item cursor-pointer"
                  data-testid={`pos-product-${product.sku}`}
                >
                  <div className="aspect-[4/3] bg-slate-100 flex items-center justify-center border-b-2 border-slate-200">
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
                      <span className="font-heading font-bold text-xl text-orange-500">
                        ${product.price.toFixed(2)}
                      </span>
                      <span className="text-xs text-slate-400">
                        {product.quantity} in stock
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Checkout Dialog */}
      <Dialog open={checkoutOpen} onOpenChange={setCheckoutOpen}>
        <DialogContent className="sm:max-w-md" data-testid="checkout-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading font-bold text-xl uppercase tracking-wider">
              Complete Sale
            </DialogTitle>
          </DialogHeader>

          <div className="py-4">
            <p className="text-sm text-slate-600 mb-4">Select Payment Method</p>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <button
                onClick={() => setPaymentMethod("cash")}
                className={`p-4 border-2 rounded-sm flex flex-col items-center gap-2 transition-colors ${
                  paymentMethod === "cash"
                    ? "border-orange-500 bg-orange-50"
                    : "border-slate-200 hover:border-slate-300"
                }`}
                data-testid="payment-cash-btn"
              >
                <Banknote className={`w-8 h-8 ${paymentMethod === "cash" ? "text-orange-500" : "text-slate-400"}`} />
                <span className={`font-semibold ${paymentMethod === "cash" ? "text-orange-500" : "text-slate-600"}`}>
                  Cash
                </span>
              </button>
              <button
                onClick={() => setPaymentMethod("card")}
                className={`p-4 border-2 rounded-sm flex flex-col items-center gap-2 transition-colors ${
                  paymentMethod === "card"
                    ? "border-orange-500 bg-orange-50"
                    : "border-slate-200 hover:border-slate-300"
                }`}
                data-testid="payment-card-btn"
              >
                <CreditCard className={`w-8 h-8 ${paymentMethod === "card" ? "text-orange-500" : "text-slate-400"}`} />
                <span className={`font-semibold ${paymentMethod === "card" ? "text-orange-500" : "text-slate-600"}`}>
                  Card
                </span>
              </button>
            </div>

            <div className="bg-slate-50 p-4 rounded-sm border-2 border-slate-200">
              <div className="flex justify-between text-lg font-bold">
                <span>Total Amount</span>
                <span className="font-mono">${total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setCheckoutOpen(false)}
              className="flex-1 btn-secondary h-12"
              data-testid="checkout-cancel-btn"
            >
              Cancel
            </Button>
            <Button
              onClick={handleCheckout}
              disabled={processing}
              className="flex-1 btn-primary h-12"
              data-testid="checkout-confirm-btn"
            >
              <Check className="w-5 h-5 mr-2" />
              {processing ? "Processing..." : "Complete Sale"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default POS;
