import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "../Login";

vi.mock("@/components/ArchExplorer", () => ({
  ArchExplorer: () => null,
}));

const mockLogin = vi.fn();
const mockRegister = vi.fn();

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    login: mockLogin,
    register: mockRegister,
  }),
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { toast } from "sonner";

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

describe("Login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("VITE_ADMIN_LOGIN_CODE", "expected-code");
  });

  it("renders sign-in form by default", () => {
    renderLogin();
    expect(screen.getByTestId("login-email-input")).toBeInTheDocument();
    expect(screen.getByTestId("login-password-input")).toBeInTheDocument();
    expect(screen.queryByTestId("signup-name-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("login-submit-btn")).toHaveTextContent("Sign in");
  });

  it("toggles to sign-up mode (contractor shows name field immediately)", () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("login-role-contractor"));
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    expect(screen.getByTestId("signup-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("login-submit-btn")).toHaveTextContent("Sign up");
  });

  it("toggles back to sign-in mode", () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    expect(screen.queryByTestId("signup-name-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("login-submit-btn")).toHaveTextContent("Sign in");
  });

  it("shows admin gate overlay with code field in signup mode for admin tab", () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    expect(screen.getByTestId("signup-admin-gate-overlay")).toBeInTheDocument();
    expect(screen.getByTestId("signup-admin-code-input")).toBeInTheDocument();
    expect(screen.getByTestId("signup-admin-unlock-btn")).toBeInTheDocument();
    expect(screen.getByTestId("signup-admin-gate-back")).toBeInTheDocument();
  });

  it("admin gate back returns to sign-in mode", () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    fireEvent.click(screen.getByTestId("signup-admin-gate-back"));
    expect(screen.queryByTestId("signup-admin-gate-overlay")).not.toBeInTheDocument();
    expect(screen.queryByTestId("signup-name-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("login-submit-btn")).toHaveTextContent("Sign in");
  });

  it("hides admin code field for contractor tab", () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("login-role-contractor"));
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    expect(screen.queryByTestId("signup-admin-code-input")).not.toBeInTheDocument();
  });

  it("rejects wrong admin code on gate unlock", async () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    fireEvent.input(screen.getByTestId("signup-admin-code-input"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByTestId("signup-admin-unlock-btn"));
    expect(mockRegister).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalled();
    expect(screen.getByTestId("signup-admin-gate-overlay")).toBeInTheDocument();
  });

  it("shows name field after unlocking admin gate", () => {
    renderLogin();
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    expect(screen.queryByTestId("signup-name-input")).not.toBeInTheDocument();
    fireEvent.input(screen.getByTestId("signup-admin-code-input"), {
      target: { value: "expected-code" },
    });
    fireEvent.click(screen.getByTestId("signup-admin-unlock-btn"));
    expect(screen.getByTestId("signup-name-input")).toBeInTheDocument();
  });

  it("calls register with role metadata on valid signup", async () => {
    mockRegister.mockResolvedValue(null);
    renderLogin();
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    fireEvent.input(screen.getByTestId("signup-admin-code-input"), {
      target: { value: "expected-code" },
    });
    fireEvent.click(screen.getByTestId("signup-admin-unlock-btn"));
    expect(screen.queryByTestId("signup-admin-gate-overlay")).not.toBeInTheDocument();
    fireEvent.input(screen.getByTestId("signup-name-input"), { target: { value: "Norm" } });
    fireEvent.input(screen.getByTestId("login-email-input"), { target: { value: "a@b.co" } });
    fireEvent.input(screen.getByTestId("login-password-input"), { target: { value: "pw123456" } });
    fireEvent.submit(screen.getByTestId("login-form"));
    await vi.waitFor(() => expect(mockRegister).toHaveBeenCalled());
    expect(mockRegister).toHaveBeenCalledWith("a@b.co", "pw123456", "Norm", "admin");
  });

  it("shows confirmation message after signup when register returns null", async () => {
    mockRegister.mockResolvedValue(null);
    renderLogin();
    fireEvent.click(screen.getByTestId("login-role-contractor"));
    fireEvent.click(screen.getByTestId("login-mode-toggle"));
    fireEvent.input(screen.getByTestId("signup-name-input"), { target: { value: "C" } });
    fireEvent.input(screen.getByTestId("login-email-input"), { target: { value: "c@d.co" } });
    fireEvent.input(screen.getByTestId("login-password-input"), { target: { value: "pw123456" } });
    fireEvent.submit(screen.getByTestId("login-form"));
    await vi.waitFor(() => expect(screen.getByTestId("signup-email-hint")).toBeInTheDocument());
    expect(screen.getByTestId("signup-email-hint")).toHaveTextContent(/email/i);
  });
});
