import { useState, useCallback, useEffect } from "react";

const STORAGE_PREFIX = "reports-visible-";

/**
 * Persisted visibility preferences for report panels per tab.
 * Returns visible panel IDs and helpers to toggle. Default: all panels visible.
 *
 * @param {string} tabId - e.g. "operations", "pl", "inventory"
 * @param {string[]} allPanelIds - full list of panel IDs for this tab
 * @returns {{ visiblePanels: Set<string>, setPanelVisible: (id: string, visible: boolean) => void, togglePanel: (id: string) => void, isVisible: (id: string) => boolean }}
 */
export function useReportLayout(tabId, allPanelIds) {
  const storageKey = `${STORAGE_PREFIX}${tabId}`;

  const [visiblePanels, setVisiblePanels] = useState(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return new Set(parsed);
      return null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (visiblePanels === null) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify([...visiblePanels]));
    } catch {
      // ignore
    }
  }, [visiblePanels, storageKey]);

  const effective = visiblePanels ?? new Set(allPanelIds);

  const setPanelVisible = useCallback(
    (id, visible) => {
      setVisiblePanels((prev) => {
        const next = new Set(prev ?? allPanelIds);
        if (visible) {
          next.add(id);
        } else {
          next.delete(id);
        }
        return next;
      });
    },
    [allPanelIds],
  );

  const togglePanel = useCallback(
    (id) => {
      setVisiblePanels((prev) => {
        const current = prev ?? new Set(allPanelIds);
        const next = new Set(current);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
        return next;
      });
    },
    [allPanelIds],
  );

  const isVisible = useCallback(
    (id) => {
      const s = visiblePanels ?? new Set(allPanelIds);
      return s.has(id);
    },
    [visiblePanels, allPanelIds],
  );

  const resetToDefault = useCallback(() => {
    setVisiblePanels(new Set(allPanelIds));
  }, [allPanelIds]);

  return {
    visiblePanels: effective,
    setPanelVisible,
    togglePanel,
    isVisible,
    resetToDefault,
  };
}
