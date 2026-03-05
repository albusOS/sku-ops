import { describe, it, expect } from "vitest";
import { getErrorMessage } from "../api-client";

describe("getErrorMessage", () => {
  it("extracts string detail from response", () => {
    const error = { response: { data: { detail: "Not found" } } };
    expect(getErrorMessage(error)).toBe("Not found");
  });

  it("joins array detail messages", () => {
    const error = {
      response: {
        data: {
          detail: [
            { msg: "field required", loc: ["body", "name"] },
            { msg: "invalid email", loc: ["body", "email"] },
          ],
        },
      },
    };
    expect(getErrorMessage(error)).toBe("field required, invalid email");
  });

  it("falls back to message field", () => {
    const error = { response: { data: { message: "Server error" } } };
    expect(getErrorMessage(error)).toBe("Server error");
  });

  it("falls back to error.message", () => {
    const error = { message: "Network Error" };
    expect(getErrorMessage(error)).toBe("Network Error");
  });

  it("returns default when nothing available", () => {
    const error = {};
    expect(getErrorMessage(error)).toBe("Something went wrong");
  });

  it("stringifies non-string non-array detail", () => {
    const error = { response: { data: { detail: { code: 42 } } } };
    expect(getErrorMessage(error)).toBe('{"code":42}');
  });
});
