import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useBarcodeScanner } from "../useBarcodeScanner";

vi.mock("@/lib/api-client", () => ({
  default: {
    products: {
      byBarcode: vi.fn(),
    },
  },
}));

import api from "@/lib/api-client";

const PRODUCT = { id: "p1", sku: "HDW-ITM-000001", name: "Test Widget" };

function makeHandlers() {
  return {
    onSuccess: vi.fn(),
    onNotFound: vi.fn(),
    onInvalidCheckDigit: vi.fn(),
  };
}

describe("useBarcodeScanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // suppress requestAnimationFrame in jsdom
    vi.stubGlobal("requestAnimationFrame", (cb) => cb());
  });

  it("calls onSuccess with product and clears input on successful scan", async () => {
    api.products.byBarcode.mockResolvedValue(PRODUCT);
    const handlers = makeHandlers();
    const { result } = renderHook(() => useBarcodeScanner(handlers));

    await act(async () => {
      result.current.setValue("HDW-ITM-000001");
      await result.current.submit("HDW-ITM-000001");
    });

    expect(api.products.byBarcode).toHaveBeenCalledWith("HDW-ITM-000001");
    expect(handlers.onSuccess).toHaveBeenCalledWith(PRODUCT);
    expect(handlers.onNotFound).not.toHaveBeenCalled();
    expect(result.current.value).toBe("");
  });

  it("calls onSuccess again for a duplicate scan (qty-increment is caller's responsibility)", async () => {
    api.products.byBarcode.mockResolvedValue(PRODUCT);
    const handlers = makeHandlers();
    const { result } = renderHook(() => useBarcodeScanner(handlers));

    await act(async () => {
      await result.current.submit("HDW-ITM-000001");
      await result.current.submit("HDW-ITM-000001");
    });

    expect(handlers.onSuccess).toHaveBeenCalledTimes(2);
  });

  it("calls onNotFound with barcode when product is not in DB", async () => {
    api.products.byBarcode.mockRejectedValue({
      response: {
        data: { detail: { code: "not_found", barcode: "HDW-ITM-999999" } },
      },
    });
    const handlers = makeHandlers();
    const { result } = renderHook(() => useBarcodeScanner(handlers));

    await act(async () => {
      await result.current.submit("HDW-ITM-999999");
    });

    expect(handlers.onNotFound).toHaveBeenCalledWith({
      barcode: "HDW-ITM-999999",
    });
    expect(handlers.onSuccess).not.toHaveBeenCalled();
    expect(result.current.value).toBe("");
  });

  it("calls onInvalidCheckDigit when backend returns invalid_check_digit", async () => {
    api.products.byBarcode.mockRejectedValue({
      response: {
        data: {
          detail: { code: "invalid_check_digit", barcode: "042100005265" },
        },
      },
    });
    const handlers = makeHandlers();
    const { result } = renderHook(() => useBarcodeScanner(handlers));

    await act(async () => {
      await result.current.submit("042100005265");
    });

    expect(handlers.onInvalidCheckDigit).toHaveBeenCalledWith("042100005265");
    expect(handlers.onNotFound).not.toHaveBeenCalled();
    expect(result.current.value).toBe("");
  });

  it("onKeyDown fires submit on Enter and ignores other keys", async () => {
    api.products.byBarcode.mockResolvedValue(PRODUCT);
    const handlers = makeHandlers();
    const { result } = renderHook(() => useBarcodeScanner(handlers));

    const preventDefault = vi.fn();

    await act(async () => {
      result.current.setValue("HDW-ITM-000001");
      // Non-Enter key — should not trigger submit
      result.current.onKeyDown({
        key: "a",
        target: { value: "HDW-ITM-000001" },
        preventDefault,
      });
    });
    expect(handlers.onSuccess).not.toHaveBeenCalled();

    await act(async () => {
      result.current.onKeyDown({
        key: "Enter",
        target: { value: "HDW-ITM-000001" },
        preventDefault,
      });
    });
    expect(preventDefault).toHaveBeenCalled();
    expect(handlers.onSuccess).toHaveBeenCalledWith(PRODUCT);
  });

  it("trims whitespace from scanned value before lookup", async () => {
    api.products.byBarcode.mockResolvedValue(PRODUCT);
    const handlers = makeHandlers();
    const { result } = renderHook(() => useBarcodeScanner(handlers));

    await act(async () => {
      await result.current.submit("  HDW-ITM-000001\n");
    });

    expect(api.products.byBarcode).toHaveBeenCalledWith("HDW-ITM-000001");
  });

  it("does nothing when submitted with empty value", async () => {
    const handlers = makeHandlers();
    const { result } = renderHook(() => useBarcodeScanner(handlers));

    await act(async () => {
      await result.current.submit("   ");
    });

    expect(api.products.byBarcode).not.toHaveBeenCalled();
  });
});
