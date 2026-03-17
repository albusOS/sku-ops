import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
import { Plus, Search, MoreHorizontal, Edit2, Trash2, Layers, Package } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { getErrorMessage } from "@/lib/api-client";
import { getDeptColor } from "@/lib/constants";
import {
  useDepartments,
  useSkuOverview,
  useCreateDepartment,
  useUpdateDepartment,
  useDeleteDepartment,
} from "@/hooks/useDepartments";

const deptSchema = z.object({
  name: z.string().min(1, "Name is required"),
  code: z.string().length(3, "Code must be exactly 3 characters"),
  description: z.string().optional().default(""),
});

const FIELDS = [
  { name: "name", label: "Category Name *", placeholder: "e.g., Lumber" },
  {
    name: "code",
    label: "Code (3 characters) *",
    placeholder: "e.g., LUM",
    maxLength: 3,
    className: "font-mono uppercase",
    disabled: (isEditing) => isEditing,
    note: "Code cannot be changed after creation",
    transform: (v) => v.toUpperCase().slice(0, 3),
  },
  {
    name: "description",
    label: "Description",
    placeholder: "Optional description",
  },
];

const DEFAULTS = { name: "", code: "", description: "" };

const Departments = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDept, setEditingDept] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({
    open: false,
    dept: null,
  });
  const [search, setSearch] = useState("");

  const { data: departments = [], isLoading, isError, error, refetch } = useDepartments();
  const { data: skuOverview } = useSkuOverview();
  const createMutation = useCreateDepartment();
  const updateMutation = useUpdateDepartment();
  const deleteMutation = useDeleteDepartment();

  const filtered = useMemo(() => {
    if (!search) return departments;
    const q = search.toLowerCase();
    return departments.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.code.toLowerCase().includes(q) ||
        d.description?.toLowerCase().includes(q),
    );
  }, [departments, search]);

  const openDialog = (dept = null) => {
    setEditingDept(dept);
    setDialogOpen(true);
  };

  const handleSubmit = async (data, isEditing) => {
    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id: editingDept.id, data });
        toast.success("Category updated!");
      } else {
        await createMutation.mutateAsync(data);
        toast.success("Category created!");
      }
      setDialogOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const handleDeleteConfirm = async () => {
    const { dept } = deleteConfirm;
    if (!dept) return;
    try {
      await deleteMutation.mutateAsync(dept.id);
      toast.success("Category deleted");
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    }
  };

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
    <div className="p-8" data-testid="departments-page">
      <PageHeader
        title="Categories"
        subtitle={`${departments.length} categories`}
        action={
          <Button
            onClick={() => openDialog()}
            className="btn-primary h-10 px-5"
            data-testid="add-department-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Category
          </Button>
        }
      />

      <div className="card-workshop p-3 mb-4 bg-muted border-border">
        <p className="text-xs text-muted-foreground">
          <strong>SKU Format:</strong>{" "}
          <span className="font-mono bg-card px-1.5 py-0.5 rounded border border-border">
            DEPT-ITM-XXXXX
          </span>{" "}
          — auto-assigned from category code + sequence when products are added.
        </p>
      </div>

      {departments.length === 0 ? (
        <div className="card-workshop p-12 text-center">
          <Layers className="w-16 h-16 mx-auto mb-4 text-muted-foreground/60" />
          <p className="text-muted-foreground font-medium">No categories yet</p>
          <p className="text-muted-foreground text-sm mb-4">
            Categories are auto-seeded on first dashboard load
          </p>
        </div>
      ) : (
        <>
          <div className="relative mb-4 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search categories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-9 input-workshop"
              data-testid="departments-search"
            />
          </div>

          <div className="card-workshop overflow-hidden" data-testid="departments-grid">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-[80px]">Code</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="hidden md:table-cell">Description</TableHead>
                  <TableHead className="w-[100px] text-right">SKUs</TableHead>
                  <TableHead className="hidden lg:table-cell w-[180px]">Next SKU</TableHead>
                  <TableHead className="w-[50px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      {search ? `No categories matching "${search}"` : "No categories"}
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((dept) => {
                    const nextSku = skuOverview?.departments?.find(
                      (d) => d.id === dept.id,
                    )?.next_sku;
                    return (
                      <TableRow key={dept.id} data-testid={`department-card-${dept.code}`}>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={`font-mono font-bold text-xs ${getDeptColor(dept.code)} border-transparent`}
                          >
                            {dept.code}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium">{dept.name}</TableCell>
                        <TableCell className="hidden md:table-cell text-muted-foreground text-xs max-w-[300px] truncate">
                          {dept.description || "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                            <Package className="w-3.5 h-3.5" />
                            {dept.sku_count || 0}
                          </span>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell font-mono text-xs text-muted-foreground">
                          {nextSku || "—"}
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
                                onClick={() => openDialog(dept)}
                                data-testid={`edit-dept-${dept.code}`}
                              >
                                <Edit2 className="w-4 h-4" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => setDeleteConfirm({ open: true, dept })}
                                className="text-destructive focus:text-destructive"
                                data-testid={`delete-dept-${dept.code}`}
                              >
                                <Trash2 className="w-4 h-4" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {search && filtered.length !== departments.length && (
            <p className="text-xs text-muted-foreground mt-2">
              Showing {filtered.length} of {departments.length} categories
            </p>
          )}
        </>
      )}

      <EntityFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Category"
        schema={deptSchema}
        fields={FIELDS}
        defaults={DEFAULTS}
        entity={editingDept}
        onSubmit={handleSubmit}
        saving={createMutation.isPending || updateMutation.isPending}
        testIdPrefix="dept"
      />

      <ConfirmDialog
        open={deleteConfirm.open}
        onOpenChange={(open) => setDeleteConfirm((p) => ({ ...p, open }))}
        title="Delete category"
        description={
          deleteConfirm.dept ? `Delete "${deleteConfirm.dept.name}"? This cannot be undone.` : ""
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleDeleteConfirm}
        variant="danger"
      />
    </div>
  );
};

export default Departments;
