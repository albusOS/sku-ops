import { useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  Plus,
  FileUp,
  Users,
  X,
  Mail,
  Phone,
  MapPin,
  User,
  Package,
  ExternalLink,
  Edit2,
  Trash2,
  Save,
  Loader2,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { useViewController } from "@/hooks/useViewController";
import { getErrorMessage } from "@/lib/api-client";
import { useVendors, useCreateVendor, useUpdateVendor, useDeleteVendor } from "@/hooks/useVendors";

const vendorSchema = z.object({
  name: z.string().min(1, "Vendor name is required"),
  contact_name: z.string().optional().default(""),
  email: z.string().email("Invalid email").or(z.literal("")).optional().default(""),
  phone: z.string().optional().default(""),
  address: z.string().optional().default(""),
});

const CREATE_FIELDS = [
  { name: "name", label: "Company Name *", placeholder: "e.g., ABC Hardware Supply" },
  { name: "contact_name", label: "Contact Name", placeholder: "e.g., John Smith" },
  { name: "email", label: "Email", type: "email", placeholder: "vendor@example.com" },
  { name: "phone", label: "Phone", placeholder: "(555) 123-4567" },
  { name: "address", label: "Address", placeholder: "123 Main St, City, State" },
];

const CREATE_DEFAULTS = { name: "", contact_name: "", email: "", phone: "", address: "" };

function InfoRow({ icon: Icon, label, value, href }) {
  if (!value) return null;
  const content = href ? (
    <a
      href={href}
      className="text-sm text-foreground hover:text-accent transition-colors underline-offset-2 hover:underline"
    >
      {value}
    </a>
  ) : (
    <span className="text-sm text-foreground">{value}</span>
  );
  return (
    <div className="flex items-start gap-3 py-2.5">
      <Icon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">{label}</p>
        {content}
      </div>
    </div>
  );
}

function VendorDetailPanel({ vendor, onClose, onUpdated, onDelete }) {
  const navigate = useNavigate();
  const updateMutation = useUpdateVendor();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const startEdit = useCallback(() => {
    setForm({
      name: vendor.name || "",
      contact_name: vendor.contact_name || "",
      email: vendor.email || "",
      phone: vendor.phone || "",
      address: vendor.address || "",
    });
    setEditing(true);
  }, [vendor]);

  const handleSave = async () => {
    try {
      const parsed = vendorSchema.parse(form);
      await updateMutation.mutateAsync({ id: vendor.id, data: parsed });
      toast.success("Vendor updated");
      setEditing(false);
      onUpdated?.();
    } catch (e) {
      if (e instanceof z.ZodError) {
        toast.error(e.errors[0]?.message || "Invalid input");
      } else {
        toast.error(getErrorMessage(e));
      }
    }
  };

  const setField = (key, value) => setForm((p) => ({ ...p, [key]: value }));

  return (
    <motion.div
      key="vendor-panel"
      initial={{ x: "100%", opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: "100%", opacity: 0 }}
      transition={{ type: "spring", stiffness: 340, damping: 38 }}
      className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden shadow-xl"
      style={{ width: "100%" }}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
              <Users className="w-4.5 h-4.5 text-accent" />
            </div>
            <div className="min-w-0">
              {editing ? (
                <Input
                  value={form.name}
                  onChange={(e) => setField("name", e.target.value)}
                  className="h-7 text-sm font-semibold"
                  autoFocus
                />
              ) : (
                <h2 className="font-semibold text-sm leading-tight truncate">{vendor.name}</h2>
              )}
              <p className="text-xs text-muted-foreground mt-0.5">
                Added {new Date(vendor.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {editing ? (
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 text-xs"
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  className="h-7 px-3 text-xs gap-1"
                  onClick={handleSave}
                  disabled={updateMutation.isPending}
                >
                  {updateMutation.isPending ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Save className="w-3 h-3" />
                  )}
                  Save
                </Button>
              </>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2 text-xs gap-1"
                onClick={startEdit}
              >
                <Edit2 className="w-3 h-3" />
                Edit
              </Button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto px-5 py-4 space-y-1">
        {editing ? (
          <div className="space-y-3">
            <EditField
              icon={User}
              label="Contact Name"
              value={form.contact_name}
              onChange={(v) => setField("contact_name", v)}
              placeholder="John Smith"
            />
            <EditField
              icon={Mail}
              label="Email"
              value={form.email}
              onChange={(v) => setField("email", v)}
              placeholder="vendor@example.com"
              type="email"
            />
            <EditField
              icon={Phone}
              label="Phone"
              value={form.phone}
              onChange={(v) => setField("phone", v)}
              placeholder="(555) 123-4567"
            />
            <EditField
              icon={MapPin}
              label="Address"
              value={form.address}
              onChange={(v) => setField("address", v)}
              placeholder="123 Main St, City, State"
            />
          </div>
        ) : (
          <div className="divide-y divide-border/40">
            <InfoRow icon={User} label="Contact" value={vendor.contact_name} />
            <InfoRow
              icon={Mail}
              label="Email"
              value={vendor.email}
              href={vendor.email ? `mailto:${vendor.email}` : undefined}
            />
            <InfoRow
              icon={Phone}
              label="Phone"
              value={vendor.phone}
              href={vendor.phone ? `tel:${vendor.phone}` : undefined}
            />
            <InfoRow icon={MapPin} label="Address" value={vendor.address} />
            {!vendor.contact_name && !vendor.email && !vendor.phone && !vendor.address && (
              <div className="py-6 text-center">
                <p className="text-sm text-muted-foreground">No contact info yet</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 text-xs gap-1"
                  onClick={startEdit}
                >
                  <Edit2 className="w-3 h-3" />
                  Add details
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer actions */}
      {!editing && (
        <div className="px-5 py-4 border-t border-border/50 shrink-0 space-y-2">
          <Button
            variant="outline"
            className="w-full gap-2 justify-center"
            onClick={() => navigate(`/purchasing?vendor=${encodeURIComponent(vendor.name)}`)}
          >
            <Package className="w-4 h-4" />
            View Purchase Orders
            <ExternalLink className="w-3 h-3 text-muted-foreground" />
          </Button>
          <Button
            variant="ghost"
            className="w-full gap-2 justify-center text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={() => onDelete(vendor)}
          >
            <Trash2 className="w-4 h-4" />
            Delete Vendor
          </Button>
        </div>
      )}
    </motion.div>
  );
}

function EditField({ icon: Icon, label, value, onChange, placeholder, type = "text" }) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="w-4 h-4 text-muted-foreground mt-2.5 shrink-0" />
      <div className="flex-1">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
        <Input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="h-8 text-sm"
        />
      </div>
    </div>
  );
}

const Vendors = () => {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, vendor: null });

  const { data: vendors = [], isLoading, isError, error, refetch } = useVendors();
  const createMutation = useCreateVendor();
  const deleteMutation = useDeleteVendor();

  const columns = useMemo(
    () => [
      {
        key: "name",
        label: "Vendor",
        type: "text",
        render: (row) => <span className="font-semibold">{row.name}</span>,
      },
      {
        key: "contact_name",
        label: "Contact",
        type: "text",
        render: (row) => (
          <span className="text-sm text-muted-foreground">{row.contact_name || "—"}</span>
        ),
      },
      {
        key: "email",
        label: "Email",
        type: "text",
        render: (row) =>
          row.email ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
              <Mail className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate max-w-[180px]">{row.email}</span>
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: "phone",
        label: "Phone",
        type: "text",
        render: (row) =>
          row.phone ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
              <Phone className="w-3.5 h-3.5 shrink-0" />
              {row.phone}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: "created_at",
        label: "Added",
        type: "date",
        align: "right",
        render: (row) =>
          row.created_at ? (
            <span className="text-xs text-muted-foreground tabular-nums">
              {new Date(row.created_at).toLocaleDateString()}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          ),
      },
    ],
    [],
  );

  const view = useViewController({ columns });
  const processed = view.apply(vendors);

  const handleCreate = async (data) => {
    try {
      await createMutation.mutateAsync(data);
      toast.success("Vendor created!");
      setDialogOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const handleDeleteConfirm = async () => {
    const { vendor } = deleteConfirm;
    if (!vendor) return;
    try {
      await deleteMutation.mutateAsync(vendor.id);
      toast.success("Vendor deleted");
      if (selectedVendor?.id === vendor.id) setSelectedVendor(null);
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    }
  };

  const panelOpen = !!selectedVendor;

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
    <TooltipProvider delayDuration={300}>
      <div className="h-full flex flex-col" data-testid="vendors-page">
        <div className="px-8 pt-8 pb-0 shrink-0">
          <PageHeader
            title="Vendors"
            subtitle={`${vendors.length} vendors`}
            action={
              <div className="flex gap-2">
                <Button
                  onClick={() => navigate("/purchasing")}
                  variant="outline"
                  className="h-12 px-6"
                >
                  <FileUp className="w-5 h-5 mr-2" />
                  Import
                </Button>
                <Button
                  onClick={() => setDialogOpen(true)}
                  className="btn-primary h-12 px-6"
                  data-testid="add-vendor-btn"
                >
                  <Plus className="w-5 h-5 mr-2" />
                  Add Vendor
                </Button>
              </div>
            }
          />
        </div>

        <div className="px-8 pt-4 shrink-0">
          <ViewToolbar
            controller={view}
            columns={columns}
            data={vendors}
            resultCount={processed.length}
          />
        </div>

        <div className="flex-1 flex min-h-0 mt-3">
          <motion.div
            layout
            animate={{ width: panelOpen ? "58%" : "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 36 }}
            className="h-full overflow-auto px-8 pb-8 shrink-0"
          >
            <DataTable
              data={processed}
              columns={view.visibleColumns}
              emptyMessage="No vendors found"
              emptyIcon={Users}
              onRowClick={(v) => setSelectedVendor(v)}
              exportable
              exportFilename="vendors.csv"
              disableSort
            />
          </motion.div>

          <AnimatePresence>
            {panelOpen && (
              <motion.div
                key="panel"
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: "42%", opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 36 }}
                className="h-full shrink-0 overflow-hidden"
              >
                <VendorDetailPanel
                  vendor={selectedVendor}
                  onClose={() => setSelectedVendor(null)}
                  onUpdated={() => {
                    refetch();
                  }}
                  onDelete={(v) => {
                    setDeleteConfirm({ open: true, vendor: v });
                  }}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <EntityFormDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          title="Vendor"
          schema={vendorSchema}
          fields={CREATE_FIELDS}
          defaults={CREATE_DEFAULTS}
          entity={null}
          onSubmit={handleCreate}
          saving={createMutation.isPending}
          testIdPrefix="vendor"
        />

        <ConfirmDialog
          open={deleteConfirm.open}
          onOpenChange={(open) => setDeleteConfirm((p) => ({ ...p, open }))}
          title="Delete vendor"
          description={
            deleteConfirm.vendor
              ? `Delete "${deleteConfirm.vendor.name}"? This cannot be undone.`
              : ""
          }
          confirmLabel="Delete"
          cancelLabel="Cancel"
          onConfirm={handleDeleteConfirm}
          variant="danger"
        />
      </div>
    </TooltipProvider>
  );
};

export default Vendors;
