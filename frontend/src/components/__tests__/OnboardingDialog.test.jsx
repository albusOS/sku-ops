import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import OnboardingDialog from "../OnboardingDialog";
import { ROLES } from "@/lib/constants";

const mockRefresh = vi.fn();
const mockOrganizations = vi.fn();
const mockCompleteProfile = vi.fn();

const authState = vi.hoisted(() => ({
  user: null,
}));

vi.mock("@/lib/api-client", () => ({
  default: {
    auth: {
      organizations: (...args) => mockOrganizations(...args),
      completeProfile: (...args) => mockCompleteProfile(...args),
    },
  },
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: authState.user,
    refreshSessionAndProfile: mockRefresh,
  }),
}));

describe("OnboardingDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = null;
    mockOrganizations.mockResolvedValue([{ id: "org-1", name: "Acme" }]);
    mockCompleteProfile.mockResolvedValue({});
    mockRefresh.mockResolvedValue(undefined);
  });

  it("renders for admin with org dropdown (no company field)", async () => {
    authState.user = { needs_onboarding: true, role: ROLES.ADMIN };
    render(<OnboardingDialog />);
    expect(await screen.findByTestId("onboarding-org-select")).toBeInTheDocument();
    expect(screen.queryByTestId("onboarding-company-input")).not.toBeInTheDocument();
    expect(screen.queryByTestId("onboarding-org-name-input")).not.toBeInTheDocument();
  });

  it("admin shows org name field when 'Create new' is selected", async () => {
    authState.user = { needs_onboarding: true, role: ROLES.ADMIN };
    render(<OnboardingDialog />);
    const sel = await screen.findByTestId("onboarding-org-select");
    fireEvent.change(sel, { target: { value: "__create_new__" } });
    expect(screen.getByTestId("onboarding-org-name-input")).toBeInTheDocument();
  });

  it("renders for contractor with company and org dropdown", async () => {
    authState.user = { needs_onboarding: true, role: ROLES.CONTRACTOR };
    render(<OnboardingDialog />);
    expect(await screen.findByTestId("onboarding-org-select")).toBeInTheDocument();
    expect(screen.getByTestId("onboarding-company-input")).toBeInTheDocument();
    expect(screen.queryByTestId("onboarding-org-name-input")).not.toBeInTheDocument();
  });

  it("submits admin onboarding (join existing org)", async () => {
    authState.user = { needs_onboarding: true, role: ROLES.ADMIN };
    render(<OnboardingDialog />);
    const sel = await screen.findByTestId("onboarding-org-select");
    fireEvent.change(sel, { target: { value: "org-1" } });
    fireEvent.input(screen.getByTestId("onboarding-phone-input"), { target: { value: "555" } });
    fireEvent.click(screen.getByTestId("onboarding-submit-btn"));
    await vi.waitFor(() => expect(mockCompleteProfile).toHaveBeenCalled());
    expect(mockCompleteProfile).toHaveBeenCalledWith({
      phone: "555",
      organization_id: "org-1",
    });
    expect(mockRefresh).toHaveBeenCalled();
  });

  it("submits admin onboarding (create new org)", async () => {
    authState.user = { needs_onboarding: true, role: ROLES.ADMIN };
    render(<OnboardingDialog />);
    const sel = await screen.findByTestId("onboarding-org-select");
    fireEvent.change(sel, { target: { value: "__create_new__" } });
    fireEvent.input(screen.getByTestId("onboarding-org-name-input"), {
      target: { value: "New Org" },
    });
    fireEvent.input(screen.getByTestId("onboarding-phone-input"), { target: { value: "555" } });
    fireEvent.click(screen.getByTestId("onboarding-submit-btn"));
    await vi.waitFor(() => expect(mockCompleteProfile).toHaveBeenCalled());
    expect(mockCompleteProfile).toHaveBeenCalledWith({
      phone: "555",
      organization_name: "New Org",
    });
    expect(mockRefresh).toHaveBeenCalled();
  });

  it("submits contractor onboarding", async () => {
    authState.user = { needs_onboarding: true, role: ROLES.CONTRACTOR };
    render(<OnboardingDialog />);
    const sel = await screen.findByTestId("onboarding-org-select");
    fireEvent.change(sel, { target: { value: "org-1" } });
    fireEvent.input(screen.getByTestId("onboarding-company-input"), { target: { value: "C2" } });
    fireEvent.click(screen.getByTestId("onboarding-submit-btn"));
    await vi.waitFor(() => expect(mockCompleteProfile).toHaveBeenCalled());
    expect(mockCompleteProfile).toHaveBeenCalledWith({
      company: "C2",
      phone: "",
      organization_id: "org-1",
    });
  });
});
