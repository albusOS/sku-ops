import { useState } from "react";
import { Link } from "react-router-dom";
import { Layers, Save, Package, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { DetailPanel, DetailSection, DetailField } from "./DetailPanel";
import { useUpdateDepartment } from "@/hooks/useDepartments";
import { getDeptColor } from "@/lib/constants";

export function DepartmentDetailPanel({ department, open, onOpenChange, skuOverview }) {
  const updateDept = useUpdateDepartment();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const startEditing = () => {
    setForm({
      name: department?.name || "",
      description: department?.description || "",
    });
    setEditing(true);
  };

  const handleSave = async () => {
    try {
      await updateDept.mutateAsync({ id: department?.id, data: form });
      toast.success("Category updated");
      setEditing(false);
    } catch {
      toast.error("Failed to update category");
    }
  };

  const handleOpenChange = (nextOpen) => {
    if (!nextOpen) setEditing(false);
    onOpenChange(nextOpen);
  };

  const nextSku = skuOverview?.departments?.find((d) => d.id === department?.id)?.next_sku;

  return (
    <DetailPanel
      open={open}
      onOpenChange={handleOpenChange}
      title={department?.name || "Category"}
      subtitle={department?.code ? `Code: ${department.code}` : undefined}
      icon={Layers}
      width="md"
      actions={
        editing ? (
          <>
            <Button variant="outline" size="sm" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={updateDept.isPending}
              className="gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              {updateDept.isPending ? "Saving…" : "Save"}
            </Button>
          </>
        ) : (
          <Button variant="outline" size="sm" onClick={startEditing}>
            Edit
          </Button>
        )
      }
    >
      {editing ? (
        <DetailSection label="Details">
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Description</label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className="mt-1 min-h-[80px]"
              />
            </div>
          </div>
        </DetailSection>
      ) : (
        <>
          <DetailSection label="Details">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Code</p>
                <Badge
                  variant="outline"
                  className={`mt-1 font-mono font-bold text-xs ${getDeptColor(department?.code)} border-transparent`}
                >
                  {department?.code}
                </Badge>
              </div>
              <DetailField label="Name" value={department?.name} />
              <div className="col-span-2">
                <DetailField label="Description" value={department?.description} />
              </div>
            </div>
          </DetailSection>

          <DetailSection label="SKU Info">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Products</p>
                {(department?.sku_count || 0) > 0 ? (
                  <Link
                    to={`/inventory?category=${encodeURIComponent(department?.name)}`}
                    className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-accent/80 font-medium mt-0.5 transition-colors"
                  >
                    <Package className="w-3.5 h-3.5" />
                    {department.sku_count}
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                ) : (
                  <p className="text-sm text-foreground mt-0.5">0</p>
                )}
              </div>
              <DetailField label="Next SKU" value={nextSku} mono />
            </div>
          </DetailSection>
        </>
      )}
    </DetailPanel>
  );
}
