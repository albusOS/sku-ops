import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Layers, Package, Trash2, MoreHorizontal, ExternalLink } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntityFormDialog } from "@/components/EntityFormDialog";
import { DataTable } from "@/components/DataTable";
import { ViewToolbar } from "@/components/ViewToolbar";
import { useViewController } from "@/hooks/useViewController";
import { getErrorMessage } from "@/lib/api-client";
import { getDeptColor } from "@/lib/constants";
import { DepartmentDetailPanel } from "@/components/DepartmentDetailPanel";
import {
  useDepartments,
  useSkuOverview,
  useCreateDepartment,
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
  const [selectedDept, setSelectedDept] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, dept: null });

  const { data: departments = [], isLoading, isError, error, refetch } = useDepartments();
  const { data: skuOverview } = useSkuOverview();
  const createMutation = useCreateDepartment();
  const deleteMutation = useDeleteDepartment();

  const columns = useMemo(
    () => [
      {
        key: "code",
        label: "Code",
        type: "text",
        render: (row) => (
          <Badge
            variant="outline"
            className={`font-mono font-bold text-xs ${getDeptColor(row.code)} border-transparent`}
          >
            {row.code}
          </Badge>
        ),
      },
      {
        key: "name",
        label: "Name",
        type: "text",
        render: (row) => <span className="font-semibold">{row.name}</span>,
      },
      {
        key: "description",
        label: "Description",
        type: "text",
        render: (row) => (
          <span className="text-xs text-muted-foreground max-w-[300px] truncate block">
            {row.description || "—"}
          </span>
        ),
      },
      {
        key: "sku_count",
        label: "Products",
        type: "number",
        align: "right",
        render: (row) => {
          const count = row.sku_count || 0;
          if (count === 0) {
            return (
              <span className="text-muted-foreground/60 tabular-nums inline-flex items-center gap-1.5">
                <Package className="w-3.5 h-3.5" />0
              </span>
            );
          }
          return (
            <Link
              to={`/inventory?category=${encodeURIComponent(row.name)}`}
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1.5 text-accent hover:text-accent/80 font-medium tabular-nums transition-colors group"
            >
              <Package className="w-3.5 h-3.5" />
              {count}
              <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          );
        },
        exportValue: (row) => row.sku_count || 0,
      },
      {
        key: "_next_sku",
        label: "Next SKU",
        sortable: false,
        filterable: false,
        searchable: false,
        render: (row) => {
          const nextSku = skuOverview?.departments?.find((d) => d.id === row.id)?.next_sku;
          return <span className="font-mono text-xs text-muted-foreground">{nextSku || "—"}</span>;
        },
      },
    ],
    [skuOverview],
  );

  const view = useViewController({ columns });
  const processed = view.apply(departments);

  const handleCreate = async (data) => {
    try {
      await createMutation.mutateAsync(data);
      toast.success("Category created!");
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
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    }
  };

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  return (
    <div className="h-full flex flex-col" data-testid="departments-page">
      <div className="px-8 pt-8 pb-0 shrink-0">
        <PageHeader
          title="Categories"
          subtitle={`${departments.length} categories`}
          action={
            <Button
              onClick={() => setDialogOpen(true)}
              className="btn-primary h-12 px-6"
              data-testid="add-department-btn"
            >
              <Plus className="w-5 h-5 mr-2" />
              Add Category
            </Button>
          }
        />
      </div>

      <div className="px-8 pt-4 shrink-0 flex items-center gap-3">
        <ViewToolbar
          controller={view}
          columns={columns}
          data={departments}
          resultCount={processed.length}
          className="flex-1"
        />
      </div>

      <div className="flex-1 min-h-0 mt-3 px-8 pb-8 overflow-auto">
        <div className="rounded-xl border border-border/40 bg-muted/30 p-3 mb-4">
          <p className="text-xs text-muted-foreground">
            <strong>SKU Format:</strong>{" "}
            <span className="font-mono bg-card px-1.5 py-0.5 rounded border border-border">
              DEPT-ITM-XXXXX
            </span>{" "}
            — auto-assigned from category code + sequence when products are added.
          </p>
        </div>

        <DataTable
          data={processed}
          columns={view.visibleColumns}
          emptyMessage="No categories yet"
          emptyIcon={Layers}
          disableSort
          onRowClick={(row) => setSelectedDept(row)}
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
              <DropdownMenuContent align="end" className="w-40">
                {(row.sku_count || 0) > 0 && (
                  <DropdownMenuItem asChild>
                    <Link to={`/inventory?category=${encodeURIComponent(row.name)}`}>
                      <Package className="w-4 h-4" />
                      View Products
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem
                  onClick={() => setDeleteConfirm({ open: true, dept: row })}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        />
      </div>

      <DepartmentDetailPanel
        department={selectedDept}
        open={!!selectedDept}
        onOpenChange={(open) => !open && setSelectedDept(null)}
        skuOverview={skuOverview}
      />

      <EntityFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Category"
        schema={deptSchema}
        fields={FIELDS}
        defaults={DEFAULTS}
        entity={null}
        onSubmit={handleCreate}
        saving={createMutation.isPending}
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
