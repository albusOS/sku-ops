import { useState, useMemo } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Plus,
  Edit2,
  Trash2,
  HardHat,
  Mail,
  Phone,
  Building2,
  ToggleLeft,
  ToggleRight,
  Search,
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
            className="btn-primary h-10 px-5"
            data-testid="add-contractor-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Contractor
          </Button>
        }
      />

      <div className="relative mb-4 max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <Input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, email, company..."
          className="pl-9 h-9 input-workshop"
          data-testid="contractor-search-input"
        />
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
        <div className="card-workshop overflow-hidden" data-testid="contractors-grid">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Name</TableHead>
                <TableHead className="hidden md:table-cell">Email</TableHead>
                <TableHead className="hidden lg:table-cell">Company</TableHead>
                <TableHead className="hidden lg:table-cell">Phone</TableHead>
                <TableHead className="hidden md:table-cell">Billing</TableHead>
                <TableHead className="w-[80px] text-center">Status</TableHead>
                <TableHead className="w-[50px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {contractors.map((contractor) => (
                <TableRow
                  key={contractor.id}
                  className={!contractor.is_active ? "opacity-50" : ""}
                  data-testid={`contractor-card-${contractor.id}`}
                >
                  <TableCell className="font-medium">{contractor.name}</TableCell>
                  <TableCell className="hidden md:table-cell">
                    <span className="inline-flex items-center gap-1.5 text-muted-foreground text-sm">
                      <Mail className="w-3.5 h-3.5" />
                      {contractor.email}
                    </span>
                  </TableCell>
                  <TableCell className="hidden lg:table-cell text-muted-foreground">
                    {contractor.company || "—"}
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    {contractor.phone ? (
                      <span className="inline-flex items-center gap-1.5 text-muted-foreground text-sm">
                        <Phone className="w-3.5 h-3.5" />
                        {contractor.phone}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground text-xs">
                    {contractor.billing_entity || "—"}
                  </TableCell>
                  <TableCell className="text-center">
                    {contractor.is_active ? (
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
                    )}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button className="p-1.5 rounded-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-44">
                        <DropdownMenuItem
                          onClick={() => openDialog(contractor)}
                          data-testid={`edit-contractor-${contractor.id}`}
                        >
                          <Edit2 className="w-4 h-4" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => toggleActive(contractor)}
                          data-testid={`toggle-contractor-${contractor.id}`}
                        >
                          {contractor.is_active ? (
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
                          onClick={() => setDeleteConfirm({ open: true, contractor })}
                          className="text-destructive focus:text-destructive"
                          data-testid={`delete-contractor-${contractor.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Billing entities — compact list, not cards */}
      <div className="mt-10">
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
