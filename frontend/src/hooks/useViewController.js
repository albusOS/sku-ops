import { useState, useMemo, useCallback } from "react";

function compareValues(a, b) {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  if (a instanceof Date && b instanceof Date) return a - b;
  return String(a).localeCompare(String(b));
}

/**
 * Simple view controller: search, dropdown/pill filters, sort, column visibility.
 *
 * Column shape (extends DataTable columns):
 *   { key, label, type?, filterable?, filterValues?, filterAccessor?,
 *     filterStyle?, sortable?, searchable? }
 *
 * type: "text" | "number" | "enum" | "date"
 * filterValues: for enum — array of strings or { value, label } objects
 * filterAccessor: (row) => value — for computed/derived columns
 * filterStyle: "pills" | "dropdown" — pills for ≤5 options, dropdown otherwise
 */
export function useViewController({ columns, initialFilters = {}, initialHiddenColumns }) {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(initialFilters);
  const [sortBy, setSortBy] = useState(null);
  const [sortDir, setSortDir] = useState("asc");
  const [hiddenColumns, setHiddenColumns] = useState(() => new Set(initialHiddenColumns || []));

  const setFilter = useCallback((key, value) => {
    setFilters((prev) => {
      if (!value) {
        const next = { ...prev };
        delete next[key];
        return next;
      }
      return { ...prev, [key]: value };
    });
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({});
    setSearch("");
  }, []);

  const setSort = useCallback((key, dir) => {
    setSortBy(key || null);
    setSortDir(dir || "asc");
  }, []);

  const toggleColumn = useCallback((key) => {
    setHiddenColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const showAllColumns = useCallback(() => setHiddenColumns(new Set()), []);

  const visibleColumns = useMemo(
    () => columns.filter((c) => !hiddenColumns.has(c.key)),
    [columns, hiddenColumns],
  );

  const apply = useCallback(
    (data) => {
      if (!data) return [];
      let result = data;

      if (search.trim()) {
        const q = search.toLowerCase().trim();
        const searchKeys = columns.filter((c) => c.searchable !== false).map((c) => c.key);
        result = result.filter((row) =>
          searchKeys.some((key) =>
            String(row[key] ?? "")
              .toLowerCase()
              .includes(q),
          ),
        );
      }

      for (const [key, value] of Object.entries(filters)) {
        const col = columns.find((c) => c.key === key);
        if (!col) continue;
        result = result.filter((row) => {
          const rv = col.filterAccessor ? col.filterAccessor(row) : row[key];
          return String(rv ?? "") === value;
        });
      }

      if (sortBy) {
        const col = columns.find((c) => c.key === sortBy);
        result = [...result].sort((a, b) => {
          const va = col?.filterAccessor ? col.filterAccessor(a) : a[sortBy];
          const vb = col?.filterAccessor ? col.filterAccessor(b) : b[sortBy];
          const cmp = compareValues(va, vb);
          return sortDir === "asc" ? cmp : -cmp;
        });
      }

      return result;
    },
    [search, filters, sortBy, sortDir, columns],
  );

  const hasActiveFilters = Object.keys(filters).length > 0 || search.trim() !== "";

  return {
    search,
    setSearch,
    filters,
    setFilter,
    clearFilters,
    sortBy,
    sortDir,
    setSort,
    hiddenColumns,
    toggleColumn,
    showAllColumns,
    visibleColumns,
    apply,
    hasActiveFilters,
  };
}
