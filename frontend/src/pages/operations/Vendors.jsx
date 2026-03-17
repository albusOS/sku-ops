import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Plus, FileUp, Users, Mail, Phone } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { VendorDetailPanel } from "@/components/VendorDetailPanel";
import { useViewController } from "@/hooks/useViewController";
import { getErrorMessage } from "@/lib/api-client";
import { useVendors, useCreateVendor, useDeleteVendor } from "@/hooks/useVendors";

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

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
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

      <div className="flex-1 min-h-0 mt-3 px-8 pb-8 overflow-auto">
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
      </div>

      <VendorDetailPanel
        vendor={selectedVendor}
        open={!!selectedVendor}
        onOpenChange={(open) => !open && setSelectedVendor(null)}
        onDelete={(v) => setDeleteConfirm({ open: true, vendor: v })}
      />

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
  );
};

export default Vendors;
