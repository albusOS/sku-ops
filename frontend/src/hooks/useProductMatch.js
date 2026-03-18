import { useState, useCallback } from "react";
import api from "@/lib/api-client";

async function fetchProducts(query) {
  const data = await api.products.list({ search: query, limit: 5 });
  return data?.items ?? (Array.isArray(data) ? data : []);
}

/**
 * Shared hook for matching extracted / PO items to existing inventory products.
 *
 * Returns per-item state: { matched, options, searching, query }
 * Used by ReviewFlow in the purchasing module.
 */
export function useProductMatch() {
  const [matches, setMatches] = useState({});

  const autoMatch = useCallback(async (items) => {
    const updates = {};
    await Promise.all(
      items.map(async (item) => {
        const key = item.id;
        const name = (item.name || "").trim();
        if (!name) return;
        try {
          updates[key] = {
            matched: null,
            options: await fetchProducts(name),
            searching: false,
            query: "",
          };
        } catch {
          updates[key] = { matched: null, options: [], searching: false, query: "" };
        }
      }),
    );
    setMatches((prev) => ({ ...prev, ...updates }));
  }, []);

  const searchMatch = useCallback(async (itemId, query) => {
    setMatches((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], searching: true, query },
    }));
    try {
      const options = await fetchProducts(query);
      setMatches((prev) => ({
        ...prev,
        [itemId]: { ...prev[itemId], options, searching: false },
      }));
    } catch {
      setMatches((prev) => ({
        ...prev,
        [itemId]: { ...prev[itemId], searching: false },
      }));
    }
  }, []);

  const confirmMatch = useCallback((itemId, product) => {
    setMatches((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], matched: product, query: "", options: [] },
    }));
  }, []);

  const clearMatch = useCallback((itemId) => {
    setMatches((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], matched: null },
    }));
  }, []);

  const reset = useCallback(() => setMatches({}), []);

  return { matches, autoMatch, searchMatch, confirmMatch, clearMatch, reset };
}
