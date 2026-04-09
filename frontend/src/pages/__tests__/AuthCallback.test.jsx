import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AuthCallback from "../AuthCallback";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

let mockUser = null;
let mockLoading = true;
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: mockLoading,
  }),
}));

const originalLocation = window.location;

function setWindowLocation(url) {
  delete window.location;
  window.location = new URL(url);
  window.location.hash = new URL(url).hash;
}

function renderCallback() {
  return render(
    <MemoryRouter initialEntries={["/auth/callback"]}>
      <AuthCallback />
    </MemoryRouter>,
  );
}

describe("AuthCallback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = null;
    mockLoading = true;
    setWindowLocation("http://localhost:3000/auth/callback");
  });

  afterEach(() => {
    window.location = originalLocation;
  });

  it("shows loading state while auth is loading", () => {
    renderCallback();
    expect(screen.getByTestId("auth-callback-loading")).toBeInTheDocument();
    expect(screen.getByText(/Confirming your email/i)).toBeInTheDocument();
  });

  it("shows success with continue button when user becomes available", async () => {
    const { rerender } = render(
      <MemoryRouter initialEntries={["/auth/callback"]}>
        <AuthCallback />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("auth-callback-loading")).toBeInTheDocument();

    mockUser = { id: "1", email: "test@test.com", role: "admin" };
    mockLoading = false;

    rerender(
      <MemoryRouter initialEntries={["/auth/callback"]}>
        <AuthCallback />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-callback-success")).toBeInTheDocument();
    });
    expect(screen.getByText(/Email verified/i)).toBeInTheDocument();
    expect(screen.getByText(/Your account has been confirmed/i)).toBeInTheDocument();
    expect(screen.getByTestId("auth-callback-continue")).toHaveTextContent(/Continue to app/i);
  });

  it("navigates to home when continue button is clicked", async () => {
    mockUser = { id: "1", email: "test@test.com", role: "admin" };
    mockLoading = false;

    renderCallback();

    await waitFor(() => {
      expect(screen.getByTestId("auth-callback-success")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("auth-callback-continue"));
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });

  it("shows error when loading finishes with no user", async () => {
    mockUser = null;
    mockLoading = false;

    renderCallback();

    await waitFor(() => {
      expect(screen.getByTestId("auth-callback-error")).toBeInTheDocument();
    });

    expect(screen.getByText(/Verification failed/i)).toBeInTheDocument();
    expect(screen.getByTestId("auth-callback-error-message")).toHaveTextContent(
      /Could not verify/i,
    );
    expect(screen.getByTestId("auth-callback-back")).toBeInTheDocument();
  });

  it("shows error when URL query has error param", async () => {
    setWindowLocation(
      "http://localhost:3000/auth/callback?error=access_denied&error_description=User+cancelled",
    );

    renderCallback();

    await waitFor(() => {
      expect(screen.getByTestId("auth-callback-error")).toBeInTheDocument();
    });

    expect(screen.getByTestId("auth-callback-error-message")).toHaveTextContent(/User cancelled/i);
  });

  it("shows error when URL hash has error param", async () => {
    setWindowLocation(
      "http://localhost:3000/auth/callback#error=server_error&error_description=Something+went+wrong",
    );

    renderCallback();

    await waitFor(() => {
      expect(screen.getByTestId("auth-callback-error")).toBeInTheDocument();
    });

    expect(screen.getByTestId("auth-callback-error-message")).toHaveTextContent(
      /Something went wrong/i,
    );
  });

  it("navigates to login when back button clicked on error", async () => {
    setWindowLocation("http://localhost:3000/auth/callback?error=test_error");

    renderCallback();

    await waitFor(() => {
      expect(screen.getByTestId("auth-callback-error")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("auth-callback-back"));
    expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
  });

  it("transitions from loading to success when user appears mid-load", async () => {
    mockUser = null;
    mockLoading = true;

    const { rerender } = render(
      <MemoryRouter initialEntries={["/auth/callback"]}>
        <AuthCallback />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("auth-callback-loading")).toBeInTheDocument();

    mockUser = { id: "1", email: "a@b.com", role: "contractor" };
    mockLoading = false;

    rerender(
      <MemoryRouter initialEntries={["/auth/callback"]}>
        <AuthCallback />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-callback-success")).toBeInTheDocument();
    });
  });
});
