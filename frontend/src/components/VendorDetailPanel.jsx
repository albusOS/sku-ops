import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Save, Package, ExternalLink, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import { format } from "date-fns";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { DetailPanel, DetailSection, DetailField } from "./DetailPanel";
import { useUpdateVendor } from "@/hooks/useVendors";
import { getErrorMessage } from "@/lib/api-client";

const vendorSchema = z.object({
  name: z.string().min(1, "Vendor name is required"),
  contact_name: z.string().optional().default(""),
  email: z.string().email("Invalid email").or(z.literal("")).optional().default(""),
  phone: z.string().optional().default(""),
  address: z.string().optional().default(""),
});

export function VendorDetailPanel({ vendor, open, onOpenChange, onDelete }) {
  const navigate = useNavigate();
  const updateMutation = useUpdateVendor();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const startEditing = () => {
    setForm({
      name: vendor?.name || "",
      contact_name: vendor?.contact_name || "",
      email: vendor?.email || "",
      phone: vendor?.phone || "",
      address: vendor?.address || "",
    });
    setEditing(true);
  };

  const handleSave = async () => {
    try {
      const parsed = vendorSchema.parse(form);
      await updateMutation.mutateAsync({ id: vendor?.id, data: parsed });
      toast.success("Vendor updated");
      setEditing(false);
    } catch (e) {
      if (e instanceof z.ZodError) {
        toast.error(e.errors[0]?.message || "Invalid input");
      } else {
        toast.error(getErrorMessage(e));
      }
    }
  };

  const handleOpenChange = (nextOpen) => {
    if (!nextOpen) setEditing(false);
    onOpenChange(nextOpen);
  };

  return (
    <DetailPanel
      open={open}
      onOpenChange={handleOpenChange}
      title={vendor?.name || "Vendor"}
      subtitle={
        vendor?.created_at
          ? `Added ${format(new Date(vendor.created_at), "MMM d, yyyy")}`
          : undefined
      }
      icon={Users}
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
              disabled={updateMutation.isPending}
              className="gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              {updateMutation.isPending ? "Saving…" : "Save"}
            </Button>
          </>
        ) : (
          <div className="flex items-center gap-2 w-full">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() =>
                navigate(`/purchasing?vendor=${encodeURIComponent(vendor?.name || "")}`)
              }
            >
              <Package className="w-3.5 h-3.5" />
              Purchase Orders
              <ExternalLink className="w-3 h-3 text-muted-foreground" />
            </Button>
            <div className="flex-1" />
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1.5"
              onClick={() => onDelete?.(vendor)}
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </Button>
            <Button variant="outline" size="sm" onClick={startEditing}>
              Edit
            </Button>
          </div>
        )
      }
    >
      {editing ? (
        <DetailSection label="Details">
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">Company Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Contact Name</label>
              <Input
                value={form.contact_name}
                onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Email</label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Phone</label>
              <Input
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Address</label>
              <Input
                value={form.address}
                onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                className="mt-1"
              />
            </div>
          </div>
        </DetailSection>
      ) : (
        <>
          <DetailSection label="Contact">
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Contact Name" value={vendor?.contact_name} />
              <DetailField label="Email" value={vendor?.email} />
              <DetailField label="Phone" value={vendor?.phone} />
              <DetailField label="Address" value={vendor?.address} />
            </div>
          </DetailSection>

          <DetailSection label="Timestamps">
            <div className="grid grid-cols-2 gap-4">
              <DetailField
                label="Created"
                value={
                  vendor?.created_at
                    ? format(new Date(vendor.created_at), "MMM d, yyyy h:mm a")
                    : undefined
                }
              />
              <DetailField
                label="Updated"
                value={
                  vendor?.updated_at
                    ? format(new Date(vendor.updated_at), "MMM d, yyyy h:mm a")
                    : undefined
                }
              />
            </div>
          </DetailSection>
        </>
      )}
    </DetailPanel>
  );
}
