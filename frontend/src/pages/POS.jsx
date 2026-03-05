import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Search,
  Plus,
  Minus,
  Trash2,
  Check,
  HardHat,
  MapPin,
  FileText,
  Clock,
  Loader2,
  ScanLine,
} from "lucide-react";
import { API } from "@/lib/api";

const IssueMaterials = () => {
  const { user } = useAuth();
  const searchRef = useRef(null);
  const dropdownRef = useRef(null);

  const [allProducts, setAllProducts] = useState([]);
  const [contractors, setContractors] = useState([]);
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  const [selectedContractor, setSelectedContractor] = useState("");
  const [jobId, setJobId] = useState("");
  const [serviceAddress, setServiceAddress] = useState("");
  const [notes, setNotes] = useState("");

  const isContractor = user?.role === "contractor";

  const searchResults = search.trim().length > 0
    ? allProducts
        .filter((p) => p.quantity > 0)
        .filter((p) => {
          const q = search.toLowerCase();
          return p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q);
        })
        .slice(0, 8)
    : [];

  useEffect(() => {
    fetchData();
    if (isContractor) setSelectedContractor(user.id);
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (
        !searchRef.current?.contains(e.target) &&
        !dropdownRef.current?.contains(e.target)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const fetchData = async () => {
    try {
      const productsRes = await axios.get(`${API}/products`);
      setAllProducts(productsRes.data);
      if (!isContractor) {
        const contractorsRes = await axios.get(`${API}/contractors`);
        setContractors(contractorsRes.data.filter((c) => c.is_active !== false));
      }
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  const addItem = (product) => {
    const existing = items.find((i) => i.product_id === product.id);
    if (existing) {
      if (existing.quantity >= product.quantity) {
        toast.error("Not enough stock");
        return;
      }
      setItems(items.map((i) =>
        i.product_id === product.id
          ? { ...i, quantity: i.quantity + 1, subtotal: (i.quantity + 1) * i.unit_price }
          : i
      ));
    } else {
      setItems([...items, {
        product_id: product.id,
        sku: product.sku,
        name: product.name,
        unit_price: product.price,
        cost: product.cost || 0,
        quantity: 1,
        subtotal: product.price,
        max_quantity: product.quantity,
        unit: product.sell_uom || "each",
      }]);
    }
    setSearch("");
    setShowDropdown(false);
    searchRef.current?.focus();
  };

  const updateQuantity = (productId, delta) => {
    setItems(
      items.map((item) => {
        if (item.product_id !== productId) return item;
        const newQty = item.quantity + delta;
        if (newQty <= 0) return null;
        if (newQty > item.max_quantity) {
          toast.error("Not enough stock");
          return item;
        }
        return { ...item, quantity: newQty, subtotal: newQty * item.unit_price };
      }).filter(Boolean)
    );
  };

  const removeItem = (productId) => {
    setItems(items.filter((i) => i.product_id !== productId));
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === "Enter" && searchResults.length > 0) {
      const exactSku = searchResults.find(
        (p) => p.sku.toLowerCase() === search.toLowerCase()
      );
      addItem(exactSku || searchResults[0]);
    }
    if (e.key === "Escape") {
      setShowDropdown(false);
      setSearch("");
    }
  };

  const subtotal = items.reduce((sum, i) => sum + i.subtotal, 0);
  const tax = subtotal * 0.08;
  const total = subtotal + tax;

  const handleSubmit = async () => {
    if (items.length === 0) { toast.error("No items added"); return; }
    if (!jobId.trim()) { toast.error("Job ID is required"); return; }
    if (!serviceAddress.trim()) { toast.error("Service address is required"); return; }
    if (!isContractor && !selectedContractor) { toast.error("Please select a contractor"); return; }

    setProcessing(true);
    try {
      const withdrawalData = {
        items: items.map(({ product_id, sku, name, quantity, unit_price, cost, subtotal, unit }) => ({
          product_id, sku, name, quantity, unit_price, cost, subtotal, unit: unit || "each",
        })),
        job_id: jobId.trim(),
        service_address: serviceAddress.trim(),
        notes: notes.trim() || null,
      };

      let withdrawal;
      if (isContractor) {
        const res = await axios.post(`${API}/withdrawals`, withdrawalData);
        withdrawal = res.data;
      } else {
        const res = await axios.post(
          `${API}/withdrawals/for-contractor?contractor_id=${selectedContractor}`,
          withdrawalData
        );
        withdrawal = res.data;
      }

      toast.success("Withdrawal logged — charged to account.");
      setItems([]);
      setJobId("");
      setServiceAddress("");
      setNotes("");
      if (!isContractor) setSelectedContractor("");
      fetchData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (typeof detail === "string" && detail.includes("Insufficient stock")) {
        toast.error(detail + " Reduce quantity or remove the item and try again.");
      } else {
        toast.error(detail || "Withdrawal failed");
      }
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex items-center gap-3 text-slate-500">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="font-medium">Loading…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-8" data-testid="pos-page">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">Issue Materials</h1>
        <p className="text-slate-500 mt-1 text-sm">Log materials going out for a job</p>
      </div>

      {/* Job Context */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-4 shadow-sm">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Job Details</p>
        <div className={`grid gap-4 ${!isContractor ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
          {!isContractor && (
            <div>
              <Label className="text-slate-600 font-medium text-sm mb-2 block">
                <HardHat className="w-4 h-4 inline mr-1" />
                Contractor
              </Label>
              <Select value={selectedContractor} onValueChange={setSelectedContractor}>
                <SelectTrigger className="input-workshop" data-testid="select-contractor">
                  <SelectValue placeholder="Select contractor" />
                </SelectTrigger>
                <SelectContent>
                  {contractors.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      <div className="flex items-center gap-2">
                        {c.name}
                        {c.company && <span className="text-slate-400 text-xs">· {c.company}</span>}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div>
            <Label className="text-slate-600 font-medium text-sm mb-2 block">
              <FileText className="w-4 h-4 inline mr-1" />
              Job ID *
            </Label>
            <Input
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              placeholder="e.g. JOB-2024-001"
              className="input-workshop"
              data-testid="job-id-input"
            />
          </div>
          <div>
            <Label className="text-slate-600 font-medium text-sm mb-2 block">
              <MapPin className="w-4 h-4 inline mr-1" />
              Service Address *
            </Label>
            <Input
              value={serviceAddress}
              onChange={(e) => setServiceAddress(e.target.value)}
              placeholder="Where are these going?"
              className="input-workshop"
              data-testid="service-address-input"
            />
          </div>
        </div>
      </div>

      {/* Quick Add */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-4 shadow-sm">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Add Items</p>
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
          <Input
            ref={searchRef}
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setShowDropdown(true); }}
            onFocus={() => search && setShowDropdown(true)}
            onKeyDown={handleSearchKeyDown}
            placeholder="Scan barcode or search by SKU / name…"
            className="input-workshop pl-12 pr-12 w-full"
            autoFocus
            data-testid="item-search-input"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300 pointer-events-none">
            <ScanLine className="w-4 h-4" />
          </span>

          {showDropdown && search.trim().length > 0 && (
            <div
              ref={dropdownRef}
              className="absolute z-20 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden"
              data-testid="search-dropdown"
            >
              {searchResults.length > 0 ? (
                searchResults.map((product) => (
                  <button
                    key={product.id}
                    onClick={() => addItem(product)}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 border-b border-slate-100 last:border-b-0 text-left transition-colors"
                    data-testid={`search-result-${product.sku}`}
                  >
                    <div>
                      <span className="font-mono text-xs text-slate-400 mr-2">{product.sku}</span>
                      <span className="font-medium text-slate-900">{product.name}</span>
                    </div>
                    <div className="flex items-center gap-4 shrink-0 ml-4">
                      <span className="text-xs text-slate-400">{product.quantity} in stock</span>
                      <span className="font-semibold text-amber-600">
                        ${product.price.toFixed(2)}
                        <span className="text-xs font-normal text-slate-400 ml-0.5">/{product.sell_uom || "ea"}</span>
                      </span>
                      <Plus className="w-4 h-4 text-slate-300" />
                    </div>
                  </button>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-slate-400">No matching products in stock</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Items List */}
      {items.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm mb-4 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Items — {items.length} line{items.length !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="divide-y divide-slate-100">
            {items.map((item) => (
              <div
                key={item.product_id}
                className="flex items-center gap-4 px-6 py-4"
                data-testid={`item-row-${item.sku}`}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-xs text-slate-400">{item.sku}</p>
                  <p className="font-semibold text-slate-900 truncate">{item.name}</p>
                  <p className="text-xs text-slate-400">${item.unit_price.toFixed(2)} / {item.unit}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => updateQuantity(item.product_id, -1)}
                    className="w-8 h-8 border border-slate-200 rounded-lg flex items-center justify-center hover:bg-slate-50 transition-colors"
                    data-testid={`qty-minus-${item.sku}`}
                  >
                    <Minus className="w-3.5 h-3.5" />
                  </button>
                  <span className="w-10 text-center font-mono font-bold text-slate-900">
                    {item.quantity}
                  </span>
                  <button
                    onClick={() => updateQuantity(item.product_id, 1)}
                    className="w-8 h-8 border border-slate-200 rounded-lg flex items-center justify-center hover:bg-slate-50 transition-colors"
                    data-testid={`qty-plus-${item.sku}`}
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="w-20 text-right shrink-0">
                  <p className="font-semibold text-slate-900">${item.subtotal.toFixed(2)}</p>
                </div>
                <button
                  onClick={() => removeItem(item.product_id)}
                  className="text-slate-300 hover:text-red-500 transition-colors shrink-0"
                  data-testid={`remove-item-${item.sku}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer: Notes + Payment + Submit */}
      {items.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
          <div>
            <Label className="text-slate-600 font-medium text-sm mb-2 block">Notes (optional)</Label>
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional notes…"
              className="input-workshop"
              data-testid="notes-input"
            />
          </div>

          <div className="flex items-center gap-2 p-3 rounded-xl bg-amber-50/80 border border-amber-200">
            <Clock className="w-5 h-5 text-amber-500 shrink-0" />
            <div>
              <span className="font-semibold text-slate-900 text-sm">Charge to Account</span>
              <p className="text-xs text-slate-500">Invoice later via Xero</p>
            </div>
          </div>

          <div className="flex items-end justify-between pt-2 border-t border-slate-100">
            <div className="space-y-1 text-sm">
              <div className="flex gap-6 text-slate-500">
                <span className="w-16">Subtotal</span>
                <span className="font-mono">${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex gap-6 text-slate-500">
                <span className="w-16">Tax (8%)</span>
                <span className="font-mono">${tax.toFixed(2)}</span>
              </div>
              <div className="flex gap-6 font-semibold text-slate-900">
                <span className="w-16">Total</span>
                <span className="font-mono">${total.toFixed(2)}</span>
              </div>
            </div>
            <Button
              onClick={handleSubmit}
              disabled={processing}
              className="btn-primary h-12 px-8"
              data-testid="checkout-btn"
            >
              {processing ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Processing…</>
              ) : (
                <><Check className="w-4 h-4 mr-2" />Log Withdrawal</>
              )}
            </Button>
          </div>
        </div>
      )}

    </div>
  );
};

export default IssueMaterials;
