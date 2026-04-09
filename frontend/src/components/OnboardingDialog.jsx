import { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { ROLES } from "@/lib/constants";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const CREATE_NEW_ORG = "__create_new__";

export default function OnboardingDialog() {
  const { user, refreshSessionAndProfile } = useAuth();
  const open = Boolean(user?.needs_onboarding);
  const [company, setCompany] = useState("");
  const [phone, setPhone] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingOrgs, setLoadingOrgs] = useState(false);

  const isAdmin = user?.role === ROLES.ADMIN;
  const isCreatingNewOrg = isAdmin && organizationId === CREATE_NEW_ORG;

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingOrgs(true);
    api.auth
      .organizations()
      .then((rows) => {
        if (!cancelled) setOrgs(Array.isArray(rows) ? rows : []);
      })
      .catch(() => {
        if (!cancelled) toast.error("Could not load organizations");
      })
      .finally(() => {
        if (!cancelled) setLoadingOrgs(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (isAdmin) {
      if (!organizationId) {
        toast.error("Select an organization or create a new one");
        return;
      }
      if (isCreatingNewOrg && !organizationName.trim()) {
        toast.error("Organization name is required");
        return;
      }
    } else {
      if (!company.trim()) {
        toast.error("Company is required");
        return;
      }
      if (!organizationId) {
        toast.error("Select an organization");
        return;
      }
    }

    setLoading(true);
    try {
      if (isAdmin) {
        await api.auth.completeProfile(
          isCreatingNewOrg
            ? { phone: phone.trim(), organization_name: organizationName.trim() }
            : { phone: phone.trim(), organization_id: organizationId },
        );
      } else {
        await api.auth.completeProfile({
          company: company.trim(),
          phone: phone.trim(),
          organization_id: organizationId,
        });
      }
      await refreshSessionAndProfile();
      toast.success("Profile complete");
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || "Could not save profile");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent
        data-testid="onboarding-dialog"
        className="[&>button.absolute]:hidden sm:max-w-md"
        onPointerDownOutside={(ev) => ev.preventDefault()}
        onEscapeKeyDown={(ev) => ev.preventDefault()}
      >
        <form onSubmit={(e) => void handleSubmit(e)}>
          <DialogHeader>
            <DialogTitle>Finish setup</DialogTitle>
            <DialogDescription>
              {isAdmin
                ? "Select an existing organization or create a new one."
                : "Join your organization and add your company details."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {!isAdmin && (
              <div className="grid gap-2">
                <Label htmlFor="onboarding-company">Company</Label>
                <Input
                  id="onboarding-company"
                  value={company}
                  onChange={(ev) => setCompany(ev.target.value)}
                  placeholder="Your company name"
                  data-testid="onboarding-company-input"
                />
              </div>
            )}
            <div className="grid gap-2">
              <Label htmlFor="onboarding-phone">Phone (optional)</Label>
              <Input
                id="onboarding-phone"
                value={phone}
                onChange={(ev) => setPhone(ev.target.value)}
                data-testid="onboarding-phone-input"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="onboarding-org">Organization</Label>
              <select
                id="onboarding-org"
                className="input-field h-10 w-full rounded-md border border-border bg-background px-3 text-sm"
                value={organizationId}
                onChange={(ev) => {
                  setOrganizationId(ev.target.value);
                  if (ev.target.value !== CREATE_NEW_ORG) {
                    setOrganizationName("");
                  }
                }}
                disabled={loadingOrgs}
                data-testid="onboarding-org-select"
              >
                <option value="">{loadingOrgs ? "Loading…" : "Select organization"}</option>
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
                {isAdmin && <option value={CREATE_NEW_ORG}>+ Create new organization</option>}
              </select>
            </div>
            {isCreatingNewOrg && (
              <div className="grid gap-2">
                <Label htmlFor="onboarding-org-name">New organization name</Label>
                <Input
                  id="onboarding-org-name"
                  value={organizationName}
                  onChange={(ev) => setOrganizationName(ev.target.value)}
                  placeholder="Enter organization name"
                  data-testid="onboarding-org-name-input"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading} data-testid="onboarding-submit-btn">
              {loading ? "Saving…" : "Continue"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
