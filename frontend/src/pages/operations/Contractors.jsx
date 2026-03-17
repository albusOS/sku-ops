import { useState, useMemo } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Plus,
  Edit2,
  Trash2,
  HardHat,
  Mail,
  Phone,
  Building2,
  DollarSign,
  CreditCard,
  ToggleLeft,
  ToggleRight,
  Search,
  User,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { BillingEntityDetailPanel } from "@/pages/identity/_BillingEntityDetailPanel";
import { ROLES } from "@/lib/constants";
import { getErrorMessage } from "@/lib/api-client";
import {
  useContractors,
  useCreateContractor,
  useUpdateContractor,
  useDeleteContractor,
} from "@/hooks/useContractors";
import { useBillingEntities, useCreateBillingEntity } from "@/hooks/useBillingEntities";

const createSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Valid email required"),
  password: z.string().min(1, "Password is required"),
  company: z.string().optional().default(""),
  billing_entity: z.string().optional().default(""),
  phone: z.string().optional().default(""),
});

const editSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Valid email required"),
  password: z.string().optional().default(""),
  company: z.string().optional().default(""),
  billing_entity: z.string().optional().default(""),
  phone: z.string().optional().default(""),
});

const FIELDS = [
  { name: "name", label: "Full Name *", placeholder: "John Smith" },
  {
    name: "email",
    label: "Email *",
    type: "email",
    placeholder: "john@company.com",
    disabled: (isEditing) => isEditing,
  },
  {
    name: "password",
    label: "Password *",
    type: "password",
    placeholder: "••••••••",
  },
  {
    name: "company",
    label: "Company",
    placeholder: "On Point / Stone & Timber / Independent",
  },
  {
    name: "billing_entity",
    label: "Billing Entity",
    placeholder: "Entity to invoice for materials",
  },
  { name: "phone", label: "Phone", placeholder: "(555) 123-4567" },
];

const DEFAULTS = {
  name: "",
  email: "",
  password: "",
  company: "",
  billing_entity: "",
  phone: "",
};

const Contractors = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingContractor, setEditingContractor] = useState(null);
  const [billingDetailId, setBillingDetailId] = useState(null);
  const [createBillingEntityOpen, setCreateBillingEntityOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState({
    open: false,
    contractor: null,
  });
  const [search, setSearch] = useState("");

  const { data: contractors = [], isLoading, isError, error, refetch } = useContractors(search);
  const { data: billingEntities = [] } = useBillingEntities();
  const createMutation = useCreateContractor();
  const updateMutation = useUpdateContractor();
  const deleteMutation = useDeleteContractor();
  const createBillingEntity = useCreateBillingEntity();

  const openDialog = (contractor = null) => {
    setEditingContractor(contractor);
    setDialogOpen(true);
  };

  const visibleFields = useMemo(
    () => (editingContractor ? FIELDS.filter((f) => f.name !== "password") : FIELDS),
    [editingContractor],
  );
  const activeBillingEntityCount = useMemo(
    () => billingEntities.filter((entity) => entity.is_active !== false).length,
    [billingEntities],
  );

  const handleSubmit = async (data, isEditing) => {
    try {
      if (isEditing) {
        const { email: _email, password: _password, ...rest } = data;
        await updateMutation.mutateAsync({
          id: editingContractor.id,
          data: rest,
        });
        toast.success("Contractor updated!");
      } else {
        await createMutation.mutateAsync({ ...data, role: ROLES.CONTRACTOR });
        toast.success("Contractor created!");
      }
      setDialogOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const handleCreateBillingEntity = async (data) => {
    try {
      const entity = await createBillingEntity.mutateAsync(data);
      toast.success(`Billing entity "${data.name}" created`);
      setCreateBillingEntityOpen(false);
      setBillingDetailId(entity.id);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const handleDeleteConfirm = async () => {
    const { contractor } = deleteConfirm;
    if (!contractor) return;
    try {
      await deleteMutation.mutateAsync(contractor.id);
      toast.success("Contractor deleted");
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    }
  };

  const toggleActive = (contractor) => {
    updateMutation.mutate(
      { id: contractor.id, data: { is_active: !contractor.is_active } },
      {
        onSuccess: () =>
          toast.success(contractor.is_active ? "Contractor disabled" : "Contractor enabled"),
        onError: () => toast.error("Failed to update contractor status"),
      },
    );
  };

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
    <div className="p-8" data-testid="contractors-page">
      <PageHeader
        title="Contractors"
        subtitle={`${contractors.length} contractor${contractors.length !== 1 ? "s" : ""} · ${billingEntities.length} billing entit${billingEntities.length !== 1 ? "ies" : "y"}`}
        action={
          <Button
            onClick={() => openDialog()}
            className="btn-primary h-12 px-6"
            data-testid="add-contractor-btn"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add Contractor
          </Button>
        }
      />

      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
          <Input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, company…"
            className="pl-10 input-workshop"
            data-testid="contractor-search-input"
          />
        </div>
      </div>

      {contractors.length === 0 ? (
        <div className="card-workshop p-12 text-center">
          <HardHat className="w-16 h-16 mx-auto mb-4 text-muted-foreground/60" />
          <p className="text-muted-foreground font-medium">
            {search.trim() ? "No contractors match your search" : "No contractors yet"}
          </p>
          <p className="text-muted-foreground text-sm mb-4">
            {search.trim()
              ? "Try a different search term"
              : "Add contractors to enable sales and ordering"}
          </p>
          <Button onClick={() => openDialog()} className="btn-primary">
            <Plus className="w-5 h-5 mr-2" />
            Add First Contractor
          </Button>
        </div>
      ) : (
        <div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          data-testid="contractors-grid"
        >
          {contractors.map((contractor) => (
            <div
              key={contractor.id}
              className={`card-workshop p-6 ${!contractor.is_active ? "opacity-60" : ""}`}
              data-testid={`contractor-card-${contractor.id}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-12 h-12 rounded-sm flex items-center justify-center ${contractor.is_active ? "bg-success/15" : "bg-muted"}`}
                  >
                    <HardHat
                      className={`w-6 h-6 ${contractor.is_active ? "text-success" : "text-muted-foreground"}`}
                    />
                  </div>
                  {!contractor.is_active && <span className="badge-error text-xs">Disabled</span>}
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => toggleActive(contractor)}
                    className="p-2 text-muted-foreground hover:text-info hover:bg-info/10 rounded-sm transition-colors"
                    title={contractor.is_active ? "Disable" : "Enable"}
                    data-testid={`toggle-contractor-${contractor.id}`}
                  >
                    {contractor.is_active ? (
                      <ToggleRight className="w-5 h-5" />
                    ) : (
                      <ToggleLeft className="w-5 h-5" />
                    )}
                  </button>
                  <button
                    onClick={() => openDialog(contractor)}
                    className="p-2 text-muted-foreground hover:text-accent hover:bg-warning/10 rounded-sm transition-colors"
                    data-testid={`edit-contractor-${contractor.id}`}
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm({ open: true, contractor })}
                    className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-sm transition-colors"
                    data-testid={`delete-contractor-${contractor.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <h3 className="font-heading font-bold text-xl text-foreground uppercase tracking-wide mb-2">
                {contractor.name}
              </h3>
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  <span>{contractor.email}</span>
                </div>
                {contractor.phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4" />
                    <span>{contractor.phone}</span>
                  </div>
                )}
                {contractor.company && (
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    <span>{contractor.company}</span>
                  </div>
                )}
                {contractor.billing_entity && (
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    <span className="text-xs">Bills to: {contractor.billing_entity}</span>
                  </div>
                )}
              </div>
              <div className="mt-4 pt-4 border-t border-border">
                <span className="text-xs text-muted-foreground">
                  Created {new Date(contractor.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-10">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Billing entities</h2>
            <p className="text-sm text-muted-foreground">
              {billingEntities.length} entit{billingEntities.length !== 1 ? "ies" : "y"} ·{" "}
              {activeBillingEntityCount} active
            </p>
          </div>
          <Button
            onClick={() => setCreateBillingEntityOpen(true)}
            variant="outline"
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            New Entity
          </Button>
        </div>

        {billingEntities.length === 0 ? (
          <div className="card-workshop p-8 text-center">
            <Building2 className="w-12 h-12 mx-auto mb-3 text-muted-foreground/60" />
            <p className="text-muted-foreground font-medium">No billing entities yet</p>
            <p className="text-muted-foreground text-sm mb-4">
              Add billing entities here to assign contractor billing accounts.
            </p>
            <Button
              onClick={() => setCreateBillingEntityOpen(true)}
              variant="outline"
              className="gap-2"
            >
              <Plus className="w-4 h-4" />
              Create First Entity
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {billingEntities.map((entity) => (
              <button
                key={entity.id}
                type="button"
                onClick={() => setBillingDetailId(entity.id)}
                className={`text-left bg-card border border-border rounded-xl p-5 shadow-sm hover:shadow-md hover:border-border transition-all ${entity.is_active === false ? "opacity-60" : ""}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-info" />
                  </div>
                </div>
                <h3 className="font-semibold text-foreground mb-2">{entity.name}</h3>
                <div className="space-y-1.5 text-sm text-muted-foreground">
                  {entity.contact_name && (
                    <div className="flex items-center gap-2">
                      <User className="w-3.5 h-3.5 text-muted-foreground" />
                      <span>{entity.contact_name}</span>
                    </div>
                  )}
                  {entity.contact_email && (
                    <div className="flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="truncate">{entity.contact_email}</span>
                    </div>
                  )}
                  {entity.payment_terms && (
                    <div className="flex items-center gap-2">
                      <CreditCard className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="capitalize">{entity.payment_terms.replace(/_/g, " ")}</span>
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <EntityFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Contractor"
        schema={editingContractor ? editSchema : createSchema}
        fields={visibleFields}
        defaults={DEFAULTS}
        entity={editingContractor}
        onSubmit={handleSubmit}
        saving={createMutation.isPending || updateMutation.isPending}
        testIdPrefix="contractor"
        presentation="sheet"
      />

      <BillingEntityDetailPanel
        entityId={billingDetailId}
        open={!!billingDetailId}
        onOpenChange={(open) => !open && setBillingDetailId(null)}
      />

      <EntityFormDialog
        open={createBillingEntityOpen}
        onOpenChange={setCreateBillingEntityOpen}
        title="Billing Entity"
        schema={z.object({
          name: z.string().min(1, "Name is required"),
          contact_name: z.string().optional().default(""),
          contact_email: z.string().email("Invalid email").or(z.literal("")).optional().default(""),
        })}
        fields={[
          { name: "name", label: "Name *", placeholder: "e.g. Acme Construction LLC" },
          { name: "contact_name", label: "Contact Name", placeholder: "Optional" },
          {
            name: "contact_email",
            label: "Contact Email",
            type: "email",
            placeholder: "Optional",
          },
        ]}
        defaults={{ name: "", contact_name: "", contact_email: "" }}
        onSubmit={handleCreateBillingEntity}
        saving={createBillingEntity.isPending}
        testIdPrefix="billing-entity"
      />

      <ConfirmDialog
        open={deleteConfirm.open}
        onOpenChange={(open) => setDeleteConfirm((p) => ({ ...p, open }))}
        title="Delete contractor"
        description={
          deleteConfirm.contractor
            ? `Delete "${deleteConfirm.contractor.name}"? This cannot be undone.`
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

export default Contractors;
