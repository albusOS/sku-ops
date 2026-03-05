import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useProductMatch } from "../useProductMatch";

vi.mock("@/lib/api-client", () => ({
  default: {
    products: {
      list: vi.fn(),
    },
  },
}));

import api from "@/lib/api-client";

describe("useProductMatch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with empty matches", () => {
    const { result } = renderHook(() => useProductMatch());
    expect(result.current.matches).toEqual({});
  });

  it("confirmMatch sets matched product", () => {
    const { result } = renderHook(() => useProductMatch());
    const product = { id: "p1", name: "Pine Board" };

    act(() => {
      result.current.confirmMatch("item-1", product);
    });

    expect(result.current.matches["item-1"].matched).toEqual(product);
    expect(result.current.matches["item-1"].query).toBe("");
    expect(result.current.matches["item-1"].options).toEqual([]);
  });

  it("clearMatch removes matched product", () => {
    const { result } = renderHook(() => useProductMatch());
    const product = { id: "p1", name: "Pine Board" };

    act(() => {
      result.current.confirmMatch("item-1", product);
    });
    expect(result.current.matches["item-1"].matched).toBeTruthy();

    act(() => {
      result.current.clearMatch("item-1");
    });
    expect(result.current.matches["item-1"].matched).toBeNull();
  });

  it("reset clears all matches", () => {
    const { result } = renderHook(() => useProductMatch());

    act(() => {
      result.current.confirmMatch("a", { id: "1" });
      result.current.confirmMatch("b", { id: "2" });
    });
    expect(Object.keys(result.current.matches).length).toBe(2);

    act(() => {
      result.current.reset();
    });
    expect(result.current.matches).toEqual({});
  });

  it("autoMatch calls API and populates options", async () => {
    const products = [{ id: "p1", name: "2x4 Board" }];
    api.products.list.mockResolvedValue(products);

    const { result } = renderHook(() => useProductMatch());

    await act(async () => {
      await result.current.autoMatch([{ id: "item-1", name: "2x4 Board" }]);
    });

    expect(api.products.list).toHaveBeenCalledWith({ search: "2x4 Board", limit: 5 });
    expect(result.current.matches["item-1"].options).toEqual(products);
    expect(result.current.matches["item-1"].searching).toBe(false);
  });

  it("autoMatch handles API errors gracefully", async () => {
    api.products.list.mockRejectedValue(new Error("fail"));

    const { result } = renderHook(() => useProductMatch());

    await act(async () => {
      await result.current.autoMatch([{ id: "item-1", name: "Board" }]);
    });

    expect(result.current.matches["item-1"].options).toEqual([]);
  });

  it("autoMatch skips items without names", async () => {
    const { result } = renderHook(() => useProductMatch());

    await act(async () => {
      await result.current.autoMatch([{ id: "item-1", name: "" }]);
    });

    expect(api.products.list).not.toHaveBeenCalled();
  });
});
