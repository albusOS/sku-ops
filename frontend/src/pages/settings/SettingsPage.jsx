import { useState, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { CheckCircle2, AlertTriangle, Link2, Link2Off, RefreshCw, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Panel, SectionHead } from "@/components/Panel";
import { API } from "@/lib/api-client";
import {
  useXeroSettings,
  useUpdateXeroSettings,
  useXeroTenants,
  useXeroTrackingCategories,
  useXeroDisconnect,
  useSelectTenant,
  useSelectTrackingCategory,
} from "@/hooks/useXeroSettings";

function ConnectionSection({ settings }) {
  const disconnect = useXeroDisconnect();
  const connected = settings?.xero_connected === true;
  const tenantId = settings?.xero_tenant_id;

  const tokenExpiringSoon = useMemo(() => {
    if (!settings?.xero_token_expiry) return false;
    try {
      const expiry = new Date(settings.xero_token_expiry);
      const hoursLeft = (expiry - Date.now()) / 3_600_000;
      return hoursLeft < 24 && hoursLeft > 0;
    } catch {
      return false;
    }
  }, [settings?.xero_token_expiry]);

  const handleConnect = () => {
    window.location.href = `${API}/xero/connect`;
  };

  const handleDisconnect = () => {
    disconnect.mutate(undefined, {
      onSuccess: () => toast.success("Xero disconnected"),
      onError: () => toast.error("Failed to disconnect Xero"),
    });
  };

  return (
    <Panel>
      <SectionHead title="Xero Connection" />
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {connected ? (
              <>
                <div className="w-8 h-8 rounded-full bg-success/15 flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4 text-success" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Connected</p>
                  <p className="text-xs text-muted-foreground">
                    Tenant: <span className="font-mono">{tenantId?.slice(0, 12)}...</span>
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                  <Link2Off className="w-4 h-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Not connected</p>
                  <p className="text-xs text-muted-foreground">
                    Connect a Xero organisation to enable invoice and bill sync
                  </p>
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            {connected ? (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive border-destructive/30 hover:bg-destructive/10"
                  >
                    <Link2Off className="w-4 h-4 mr-2" />
                    Disconnect
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Disconnect Xero?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will remove all OAuth tokens. Invoices, credit notes, and PO bills will
                      stop syncing until you reconnect.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleDisconnect}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Disconnect
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            ) : (
              <Button onClick={handleConnect} size="sm" className="gap-2">
                <Link2 className="w-4 h-4" />
                Connect Xero
              </Button>
            )}
          </div>
        </div>

        {tokenExpiringSoon && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-warning/10 border border-warning/30 text-sm text-accent">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            Access token expires within 24 hours. Reconnect to refresh credentials.
          </div>
        )}
      </div>
    </Panel>
  );
}

function TenantTrackingSection({ settings }) {
  const { data: tenantsData, isLoading: tenantsLoading } = useXeroTenants(settings?.xero_connected);
  const { data: categoriesData, isLoading: catsLoading } = useXeroTrackingCategories(
    settings?.xero_connected,
  );
  const selectTenant = useSelectTenant();
  const selectCategory = useSelectTrackingCategory();

  const tenants = tenantsData?.tenants || [];
  const categories = categoriesData?.tracking_categories || [];

  const handleTenantChange = (value) => {
    selectTenant.mutate(value, {
      onSuccess: () => toast.success("Xero tenant updated"),
      onError: () => toast.error("Failed to update tenant"),
    });
  };

  const handleCategoryChange = (value) => {
    selectCategory.mutate(value, {
      onSuccess: () => toast.success("Tracking category updated"),
      onError: () => toast.error("Failed to update tracking category"),
    });
  };

  if (!settings?.xero_connected) return null;

  return (
    <Panel>
      <SectionHead title="Organisation & Tracking" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <Label className="text-muted-foreground text-sm font-medium">Xero Organisation</Label>
          <Select
            value={settings.xero_tenant_id || ""}
            onValueChange={handleTenantChange}
            disabled={tenantsLoading || selectTenant.isPending}
          >
            <SelectTrigger className="mt-2">
              <SelectValue placeholder={tenantsLoading ? "Loading..." : "Select organisation"} />
            </SelectTrigger>
            <SelectContent>
              {tenants.map((t) => (
                <SelectItem key={t.tenantId} value={t.tenantId}>
                  {t.tenantName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground mt-1.5">
            The Xero org where invoices, credit notes, and bills are posted
          </p>
        </div>

        <div>
          <Label className="text-muted-foreground text-sm font-medium">Job Tracking Category</Label>
          <Select
            value={settings.xero_tracking_category_id || ""}
            onValueChange={handleCategoryChange}
            disabled={catsLoading || selectCategory.isPending}
          >
            <SelectTrigger className="mt-2">
              <SelectValue placeholder={catsLoading ? "Loading..." : "None (optional)"} />
            </SelectTrigger>
            <SelectContent>
              {categories.map((c) => (
                <SelectItem key={c.TrackingCategoryID} value={c.TrackingCategoryID}>
                  {c.Name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground mt-1.5">
            Tags invoice lines with the job ID as a Xero tracking option
          </p>
        </div>
      </div>
    </Panel>
  );
}

function AccountCodesSection({ settings }) {
  const update = useUpdateXeroSettings();

  const [form, setForm] = useState({
    xero_sales_account_code: "",
    xero_cogs_account_code: "",
    xero_inventory_account_code: "",
    xero_ap_account_code: "",
    default_tax_rate: "",
    xero_tax_type: "",
  });
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!settings) return;
    setForm({
      xero_sales_account_code: settings.xero_sales_account_code || "",
      xero_cogs_account_code: settings.xero_cogs_account_code || "",
      xero_inventory_account_code: settings.xero_inventory_account_code || "",
      xero_ap_account_code: settings.xero_ap_account_code || "",
      default_tax_rate:
        settings.default_tax_rate != null
          ? String(Math.round(settings.default_tax_rate * 100))
          : "",
      xero_tax_type: settings.xero_tax_type || "",
    });
    setDirty(false);
  }, [settings]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setDirty(true);
  };

  const handleSave = () => {
    const payload = {
      xero_sales_account_code: form.xero_sales_account_code || null,
      xero_cogs_account_code: form.xero_cogs_account_code || null,
      xero_inventory_account_code: form.xero_inventory_account_code || null,
      xero_ap_account_code: form.xero_ap_account_code || null,
      xero_tax_type: form.xero_tax_type || null,
    };
    const rate = parseFloat(form.default_tax_rate);
    if (!isNaN(rate)) payload.default_tax_rate = rate / 100;

    update.mutate(payload, {
      onSuccess: () => {
        toast.success("Settings saved");
        setDirty(false);
      },
      onError: () => toast.error("Failed to save settings"),
    });
  };

  const FIELDS = [
    {
      key: "xero_sales_account_code",
      label: "Sales / Revenue Account",
      hint: "Xero account code for revenue lines (e.g. 200)",
    },
    {
      key: "xero_cogs_account_code",
      label: "COGS Account",
      hint: "Cost of goods sold journal debit (e.g. 500)",
    },
    {
      key: "xero_inventory_account_code",
      label: "Inventory Account",
      hint: "Inventory asset — credited on COGS journals, debited on PO bills (e.g. 630)",
    },
    {
      key: "xero_ap_account_code",
      label: "Accounts Payable Account",
      hint: "Trade creditors / AP account (e.g. 800)",
    },
  ];

  return (
    <Panel>
      <SectionHead title="Account Codes & Tax" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
        {FIELDS.map((f) => (
          <div key={f.key}>
            <Label htmlFor={f.key} className="text-muted-foreground text-sm font-medium">
              {f.label}
            </Label>
            <Input
              id={f.key}
              value={form[f.key]}
              onChange={(e) => handleChange(f.key, e.target.value)}
              className="input-field mt-2 font-mono"
              placeholder="—"
            />
            <p className="text-xs text-muted-foreground mt-1">{f.hint}</p>
          </div>
        ))}

        <div>
          <Label htmlFor="default_tax_rate" className="text-muted-foreground text-sm font-medium">
            Default Tax Rate (%)
          </Label>
          <Input
            id="default_tax_rate"
            type="number"
            min="0"
            max="100"
            step="0.1"
            value={form.default_tax_rate}
            onChange={(e) => handleChange("default_tax_rate", e.target.value)}
            className="input-field mt-2 font-mono"
            placeholder="10"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Applied to new invoices (e.g. 10 for 10% GST)
          </p>
        </div>

        <div>
          <Label htmlFor="xero_tax_type" className="text-muted-foreground text-sm font-medium">
            Xero Tax Type
          </Label>
          <Input
            id="xero_tax_type"
            value={form.xero_tax_type}
            onChange={(e) => handleChange("xero_tax_type", e.target.value)}
            className="input-field mt-2 font-mono"
            placeholder="e.g. OUTPUT2"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Xero tax type tag on invoice lines (leave empty for no tax tagging)
          </p>
        </div>
      </div>

      <div className="flex justify-end mt-6">
        <Button onClick={handleSave} disabled={!dirty || update.isPending} className="gap-2">
          {update.isPending ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {update.isPending ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </Panel>
  );
}

export default function SettingsPage() {
  const { data: settings, isLoading } = useXeroSettings();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    if (searchParams.get("xero") === "connected") {
      toast.success("Xero connected successfully");
      searchParams.delete("xero");
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  if (isLoading) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center text-muted-foreground text-sm">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 md:p-8 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Xero integration, account mapping, and tax configuration
        </p>
      </div>

      <ConnectionSection settings={settings} />
      <TenantTrackingSection settings={settings} />
      <AccountCodesSection settings={settings} />
    </div>
  );
}
