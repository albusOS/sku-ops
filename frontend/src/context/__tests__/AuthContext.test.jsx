import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "../AuthContext";

const signUp = vi.fn();
const getSession = vi.fn();

vi.mock("@/lib/api-client", () => ({
  default: {
    auth: {
      me: vi.fn(),
    },
  },
}));

vi.mock("@/lib/supabase", () => ({
  isSupabaseConfigured: true,
  getSupabase: vi.fn(() =>
    Promise.resolve({
      auth: {
        signUp,
        getSession,
        onAuthStateChange: vi.fn(() => ({
          data: { subscription: { unsubscribe: vi.fn() } },
        })),
      },
    }),
  ),
}));

import api from "@/lib/api-client";

function RegisterProbe() {
  const { register } = useAuth();
  return (
    <button
      type="button"
      data-testid="do-register"
      onClick={() => void register("e@e.com", "secret12", "Pat", "contractor")}
    >
      reg
    </button>
  );
}

describe("AuthProvider register", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    signUp.mockResolvedValue({ data: { session: null }, error: null });
    getSession.mockResolvedValue({ data: { session: null } });
    api.auth.me.mockResolvedValue({
      id: "1",
      email: "e@e.com",
      name: "Pat",
      role: "contractor",
      organization_id: "",
      needs_onboarding: true,
    });
  });

  it("register passes role in signUp user metadata", async () => {
    render(
      <AuthProvider>
        <RegisterProbe />
      </AuthProvider>,
    );
    fireEvent.click(screen.getByTestId("do-register"));
    await waitFor(() => expect(signUp).toHaveBeenCalled());
    expect(signUp).toHaveBeenCalledWith({
      email: "e@e.com",
      password: "secret12",
      options: { data: { name: "Pat", role: "contractor" } },
    });
  });
});

function MeProbe() {
  const { user } = useAuth();
  return <div data-testid="needs">{user?.needs_onboarding ? "yes" : "no"}</div>;
}

describe("AuthProvider profile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSession.mockResolvedValue({
      data: { session: { access_token: "tok" } },
    });
    signUp.mockResolvedValue({ data: { session: null }, error: null });
    api.auth.me.mockResolvedValue({
      id: "1",
      email: "e@e.com",
      name: "Pat",
      role: "admin",
      organization_id: "",
      needs_onboarding: true,
    });
  });

  it("sets needsOnboarding when profile reports needs_onboarding", async () => {
    render(
      <AuthProvider>
        <MeProbe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("needs")).toHaveTextContent("yes"));
  });
});
