import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { CheckCircle, X, Search, Loader2, PackagePlus, ChevronDown } from "lucide-react";

/**
 * Inline widget for matching an item to an existing inventory product.
 *
 * When autoMatch returns suggestions, the top result is shown as an inline
 * pill the user can accept with one click — no need to open a search box first.
 *
 * @param {object|null} matched        The confirmed matched product (or null)
 * @param {array}       options        Search result candidates from autoMatch
 * @param {boolean}     searching      Whether a search is in progress
 * @param {function}    onSearch       (query: string) => void
 * @param {function}    onConfirm      (product: object) => void
 * @param {function}    onClear        () => void
 */
export function ProductMatchPicker({
  matched,
  options = [],
  searching = false,
  onSearch,
  onConfirm,
  onClear,
}) {
  const [query, setQuery] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [manualSearch, setManualSearch] = useState(false);
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowDropdown(false);
        setManualSearch(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (manualSearch && inputRef.current) inputRef.current.focus();
  }, [manualSearch]);

  const handleQueryChange = (val) => {
    setQuery(val);
    setShowDropdown(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.trim().length >= 2) {
      debounceRef.current = setTimeout(() => onSearch?.(val.trim()), 350);
    }
  };

  const handleSelect = (product) => {
    onConfirm?.(product);
    setQuery("");
    setShowDropdown(false);
    setManualSearch(false);
  };

  const handleClear = () => {
    onClear?.();
    setQuery("");
    setManualSearch(false);
  };

  if (matched) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-success/10 border border-success/30 text-xs">
        <CheckCircle className="w-3.5 h-3.5 text-success shrink-0" />
        <span className="font-mono text-success font-semibold">{matched.sku}</span>
        <span className="text-foreground truncate flex-1">{matched.name}</span>
        <span className="text-muted-foreground tabular-nums shrink-0">
          qty: {matched.quantity ?? 0}
        </span>
        <button
          type="button"
          onClick={handleClear}
          className="p-0.5 text-muted-foreground hover:text-destructive transition-colors"
          title="Remove match"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  const topSuggestion = options.length > 0 ? options[0] : null;
  const hasMultiple = options.length > 1;

  if (topSuggestion && !manualSearch) {
    return (
      <div ref={wrapperRef} className="relative">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-info/8 border border-info/25 text-xs">
          <Search className="w-3.5 h-3.5 text-info shrink-0" />
          <span className="text-muted-foreground shrink-0">Suggested:</span>
          <span className="font-mono text-info font-semibold">{topSuggestion.sku}</span>
          <span className="text-foreground truncate flex-1">{topSuggestion.name}</span>
          <button
            type="button"
            onClick={() => handleSelect(topSuggestion)}
            className="px-2 py-0.5 rounded-md bg-success/15 text-success font-semibold hover:bg-success/25 transition-colors shrink-0"
          >
            Accept
          </button>
          {hasMultiple && (
            <button
              type="button"
              onClick={() => {
                setShowDropdown(true);
                setManualSearch(true);
              }}
              className="p-0.5 text-muted-foreground hover:text-foreground transition-colors shrink-0"
              title="See more options"
            >
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            type="button"
            onClick={() => setManualSearch(true)}
            className="p-0.5 text-muted-foreground hover:text-foreground transition-colors shrink-0"
            title="Search manually"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {showDropdown && <DropdownList options={options} onSelect={handleSelect} />}
      </div>
    );
  }

  return (
    <div ref={wrapperRef} className="relative">
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-warning/10 border border-warning/30 text-[10px] font-semibold text-warning shrink-0">
          <PackagePlus className="w-3 h-3" />
          New
        </span>
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            onFocus={() => {
              if (options.length > 0 || query.length >= 2) setShowDropdown(true);
            }}
            placeholder="Search existing product…"
            className="h-8 text-xs pl-7 pr-2"
          />
          {searching && (
            <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground animate-spin" />
          )}
        </div>
      </div>

      {showDropdown && options.length > 0 && (
        <DropdownList options={options} onSelect={handleSelect} />
      )}

      {showDropdown && query.length >= 2 && !searching && options.length === 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-card border border-border rounded-lg shadow-lg px-3 py-2 text-xs text-muted-foreground">
          No matches found — will create as new product
        </div>
      )}
    </div>
  );
}

function DropdownList({ options, onSelect }) {
  return (
    <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-card border border-border rounded-lg shadow-lg max-h-48 overflow-auto">
      {options.map((product) => (
        <button
          key={product.id}
          type="button"
          onClick={() => onSelect(product)}
          className="w-full text-left px-3 py-2 hover:bg-muted flex items-center gap-2 text-xs border-b border-border/50 last:border-0 transition-colors"
        >
          <span className="font-mono font-semibold text-foreground shrink-0">{product.sku}</span>
          <span className="text-muted-foreground truncate flex-1">{product.name}</span>
          <span className="text-muted-foreground tabular-nums shrink-0">
            qty: {product.quantity ?? 0}
          </span>
        </button>
      ))}
    </div>
  );
}
