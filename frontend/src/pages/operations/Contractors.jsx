import { useState, useMemo } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Plus,
  Trash2,
  HardHat,
  Mail,
  Phone,
  Building2,
  ToggleLeft,
  ToggleRight,
  MoreHorizontal,
  User,
  CreditCard,
  ChevronRight,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { DataTable } from "@/components/DataTable";
import { ContractorDetailPanel } from "@/components/ContractorDetailPanel";
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

const CREATE_FIELDS = [
  { name: "name", label: "Full Name *", placeholder: "John Smith" },
  { name: "email", label: "Email *", type: "email", placeholder: "john@company.com" },
  { name: "password", label: "Password *", type: "password", placeholder: "••••••••" },
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

const CREATE_DEFAULTS = {
  name: "",
  email: "",
  password: "",
  company: "",
  billing_entity: "",
  phone: "",
};

const Contractors = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedContractor, setSelectedContractor] = useState(null);
  const [billingDetailId, setBillingDetailId] = useState(null);
  const [createBillingEntityOpen, setCreateBillingEntityOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState({
    open: false,
    contractor: null,
  });

  const { data: contractors = [], isLoading, isError, error, refetch } = useContractors();
  const { data: billingEntities = [] } = useBillingEntities();
  const createMutation = useCreateContractor();
  const updateMutation = useUpdateContractor();
  const deleteMutation = useDeleteContractor();
  const createBillingEntity = useCreateBillingEntity();

  const activeBillingEntityCount = useMemo(
    () => billingEntities.filter((entity) => entity.is_active !== false).length,
    [billingEntities],
  );

  const columns = useMemo(
    () => [
      {
        key: "name",
        label: "Name",
        render: (row) => <span className="font-medium">{row.name}</span>,
      },
      {
        key: "email",
        label: "Email",
        render: (row) => (
          <span className="inline-flex items-center gap-1.5 text-muted-foreground text-sm">
            <Mail className="w-3.5 h-3.5" />
            {row.email}
          </span>
        ),
      },
      {
        key: "company",
        label: "Company",
        render: (row) => <span className="text-muted-foreground">{row.company || "—"}</span>,
      },
      {
        key: "phone",
        label: "Phone",
        render: (row) =>
          row.phone ? (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground text-sm">
              <Phone className="w-3.5 h-3.5" />
              {row.phone}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: "billing_entity",
        label: "Billing",
        render: (row) => (
          <span className="text-muted-foreground text-xs">{row.billing_entity || "—"}</span>
        ),
      },
      {
        key: "is_active",
        label: "Status",
        align: "center",
        render: (row) =>
          row.is_active ? (
            <Badge
              variant="outline"
              className="bg-success/10 text-success border-success/20 text-xs"
            >
              Active
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="bg-destructive/10 text-destructive border-destructive/20 text-xs"
            >
              Disabled
            </Badge>
          ),
      },
    ],
    [],
  );

  const handleCreate = async (data) => {
    try {
      await createMutation.mutateAsync({ ...data, role: ROLES.CONTRACTOR });
      toast.success("Contractor created!");
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
      if (selectedContractor?.id === contractor.id) setSelectedContractor(null);
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
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
    <div className="h-full flex flex-col" data-testid="contractors-page">
      <div className="px-8 pt-8 pb-0 shrink-0">
        <PageHeader
          title="Contractors"
          subtitle={`${contractors.length} contractor${contractors.length !== 1 ? "s" : ""} · ${billingEntities.length} billing entit${billingEntities.length !== 1 ? "ies" : "y"}`}
          action={
            <Button
              onClick={() => setDialogOpen(true)}
              className="btn-primary h-10 px-5"
              data-testid="add-contractor-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Contractor
            </Button>
          }
        />
      </div>

      <div className="flex-1 min-h-0 mt-4 px-8 pb-4 overflow-auto">
        <DataTable
          data={contractors}
          columns={columns}
          emptyMessage="No contractors yet"
          emptyIcon={HardHat}
          searchable
          onRowClick={(row) => setSelectedContractor(row)}
          rowActions={(row) => (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="p-1.5 rounded-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44">
                <DropdownMenuItem
                  onClick={() => toggleActive(row)}
                  data-testid={`toggle-contractor-${row.id}`}
                >
                  {row.is_active ? (
                    <>
                      <ToggleLeft className="w-4 h-4" />
                      Disable
                    </>
                  ) : (
                    <>
                      <ToggleRight className="w-4 h-4" />
                      Enable
                    </>
                  )}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => setDeleteConfirm({ open: true, contractor: row })}
                  className="text-destructive focus:text-destructive"
                  data-testid={`delete-contractor-${row.id}`}
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        />
      </div>

      {/* Billing entities — compact list */}
      <div className="px-8 pb-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Billing Entities</h2>
            <p className="text-sm text-muted-foreground">
              {billingEntities.length} entit{billingEntities.length !== 1 ? "ies" : "y"} ·{" "}
              {activeBillingEntityCount} active
            </p>
          </div>
          <Button
            onClick={() => setCreateBillingEntityOpen(true)}
            variant="outline"
            className="gap-2 h-9"
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
          <div className="card-workshop overflow-hidden divide-y divide-border">
            {billingEntities.map((entity) => (
              <button
                key={entity.id}
                type="button"
                onClick={() => setBillingDetailId(entity.id)}
                className={`w-full flex items-center gap-4 px-4 py-3 text-left hover:bg-muted/50 transition-colors ${entity.is_active === false ? "opacity-50" : ""}`}
              >
                <div className="w-8 h-8 rounded-md bg-info/10 flex items-center justify-center shrink-0">
                  <Building2 className="w-4 h-4 text-info" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-foreground truncate">{entity.name}</p>
                  <div className="flex items-center gap-3 mt-0.5">
                    {entity.contact_name && (
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <User className="w-3 h-3" />
                        {entity.contact_name}
                      </span>
                    )}
                    {entity.contact_email && (
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <Mail className="w-3 h-3" />
                        {entity.contact_email}
                      </span>
                    )}
                    {entity.payment_terms && (
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <CreditCard className="w-3 h-3" />
                        <span className="capitalize">
                          {entity.payment_terms.replace(/_/g, " ")}
                        </span>
                      </span>
                    )}
                  </div>
                </div>
                {entity.is_active === false && (
                  <Badge
                    variant="outline"
                    className="bg-destructive/10 text-destructive border-destructive/20 text-xs shrink-0"
                  >
                    Inactive
                  </Badge>
                )}
                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
              </button>
            ))}
          </div>
        )}
      </div>

      <ContractorDetailPanel
        contractor={selectedContractor}
        open={!!selectedContractor}
        onOpenChange={(open) => !open && setSelectedContractor(null)}
      />

      <EntityFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Contractor"
        schema={createSchema}
        fields={CREATE_FIELDS}
        defaults={CREATE_DEFAULTS}
        entity={null}
        onSubmit={handleCreate}
        saving={createMutation.isPending}
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
