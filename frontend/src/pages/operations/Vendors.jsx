import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Plus,
  Search,
  MoreHorizontal,
  Edit2,
  Trash2,
  Users,
  FileUp,
  Mail,
  Phone,
} from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { getErrorMessage } from "@/lib/api-client";
import { useVendors, useCreateVendor, useUpdateVendor, useDeleteVendor } from "@/hooks/useVendors";

const vendorSchema = z.object({
  name: z.string().min(1, "Vendor name is required"),
  contact_name: z.string().optional().default(""),
  email: z.string().email("Invalid email").or(z.literal("")).optional().default(""),
  phone: z.string().optional().default(""),
  address: z.string().optional().default(""),
});

const FIELDS = [
  {
    name: "name",
    label: "Company Name *",
    placeholder: "e.g., ABC Hardware Supply",
  },
  {
    name: "contact_name",
    label: "Contact Name",
    placeholder: "e.g., John Smith",
  },
  {
    name: "email",
    label: "Email",
    type: "email",
    placeholder: "vendor@example.com",
  },
  { name: "phone", label: "Phone", placeholder: "(555) 123-4567" },
  {
    name: "address",
    label: "Address",
    placeholder: "123 Main St, City, State",
  },
];

const DEFAULTS = {
  name: "",
  contact_name: "",
  email: "",
  phone: "",
  address: "",
};

const Vendors = () => {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({
    open: false,
    vendor: null,
  });
  const [search, setSearch] = useState("");

  const { data: vendors = [], isLoading, isError, error, refetch } = useVendors();
  const createMutation = useCreateVendor();
  const updateMutation = useUpdateVendor();
  const deleteMutation = useDeleteVendor();

  const filtered = useMemo(() => {
    if (!search) return vendors;
    const q = search.toLowerCase();
    return vendors.filter(
      (v) =>
        v.name.toLowerCase().includes(q) ||
        v.contact_name?.toLowerCase().includes(q) ||
        v.email?.toLowerCase().includes(q) ||
        v.phone?.toLowerCase().includes(q),
    );
  }, [vendors, search]);

  const openDialog = (vendor = null) => {
    setEditingVendor(vendor);
    setDialogOpen(true);
  };

  const handleSubmit = async (data, isEditing) => {
    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id: editingVendor.id, data });
        toast.success("Vendor updated!");
      } else {
        await createMutation.mutateAsync(data);
        toast.success("Vendor created!");
      }
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
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    }
  };

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
    <div className="p-8" data-testid="vendors-page">
      <PageHeader
        title="Vendors"
        subtitle={`${vendors.length} vendors`}
        action={
          <div className="flex gap-2">
            <Button
              onClick={() => navigate("/purchasing")}
              variant="outline"
              className="h-10 px-5"
              data-testid="import-document-btn"
            >
              <FileUp className="w-4 h-4 mr-2" />
              Import
            </Button>
            <Button
              onClick={() => openDialog()}
              className="btn-primary h-10 px-5"
              data-testid="add-vendor-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Vendor
            </Button>
          </div>
        }
      />

      {vendors.length === 0 ? (
        <div className="card-workshop p-12">
          <EmptyState
            icon={Users}
            title="No vendors yet"
            description="Add vendors to track your suppliers"
            action={
              <Button onClick={() => openDialog()} className="btn-primary">
                <Plus className="w-5 h-5 mr-2" />
                Add First Vendor
              </Button>
            }
          />
        </div>
      ) : (
        <>
          <div className="relative mb-4 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search vendors..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-9 input-workshop"
              data-testid="vendors-search"
            />
          </div>

          <div className="card-workshop overflow-hidden" data-testid="vendors-grid">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Name</TableHead>
                  <TableHead className="hidden md:table-cell">Contact</TableHead>
                  <TableHead className="hidden lg:table-cell">Email</TableHead>
                  <TableHead className="hidden lg:table-cell">Phone</TableHead>
                  <TableHead className="w-[50px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      {search ? `No vendors matching "${search}"` : "No vendors"}
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((vendor) => (
                    <TableRow key={vendor.id} data-testid={`vendor-card-${vendor.id}`}>
                      <TableCell className="font-medium">{vendor.name}</TableCell>
                      <TableCell className="hidden md:table-cell text-muted-foreground">
                        {vendor.contact_name || "—"}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        {vendor.email ? (
                          <a
                            href={`mailto:${vendor.email}`}
                            className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
                          >
                            <Mail className="w-3.5 h-3.5" />
                            {vendor.email}
                          </a>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        {vendor.phone ? (
                          <span className="inline-flex items-center gap-1.5 text-muted-foreground text-sm">
                            <Phone className="w-3.5 h-3.5" />
                            {vendor.phone}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button className="p-1.5 rounded-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                              <MoreHorizontal className="w-4 h-4" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-36">
                            <DropdownMenuItem
                              onClick={() => openDialog(vendor)}
                              data-testid={`edit-vendor-${vendor.id}`}
                            >
                              <Edit2 className="w-4 h-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => setDeleteConfirm({ open: true, vendor })}
                              className="text-destructive focus:text-destructive"
                              data-testid={`delete-vendor-${vendor.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {search && filtered.length !== vendors.length && (
            <p className="text-xs text-muted-foreground mt-2">
              Showing {filtered.length} of {vendors.length} vendors
            </p>
          )}
        </>
      )}

      <EntityFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Vendor"
        schema={vendorSchema}
        fields={FIELDS}
        defaults={DEFAULTS}
        entity={editingVendor}
        onSubmit={handleSubmit}
        saving={createMutation.isPending || updateMutation.isPending}
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
