import { useState } from "react";
import { HardHat, Save } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { DetailPanel, DetailSection, DetailField } from "./DetailPanel";
import { useUpdateContractor } from "@/hooks/useContractors";

export function ContractorDetailPanel({ contractor, open, onOpenChange }) {
  const updateContractor = useUpdateContractor();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const startEditing = () => {
    setForm({
      name: contractor?.name || "",
      company: contractor?.company || "",
      phone: contractor?.phone || "",
    });
    setEditing(true);
  };

  const handleSave = async () => {
    try {
      await updateContractor.mutateAsync({ id: contractor?.id, data: form });
      toast.success("Contractor updated");
      setEditing(false);
    } catch {
      toast.error("Failed to update contractor");
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
      title={contractor?.name || "Contractor"}
      subtitle={contractor?.email}
      status={contractor?.is_active ? "active" : "disabled"}
      icon={HardHat}
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
              disabled={updateContractor.isPending}
              className="gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              {updateContractor.isPending ? "Saving…" : "Save"}
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
              <label className="text-xs text-muted-foreground">Company</label>
              <Input
                value={form.company}
                onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
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
          </div>
        </DetailSection>
      ) : (
        <>
          <DetailSection label="Details">
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Name" value={contractor?.name} />
              <DetailField label="Email" value={contractor?.email} />
              <DetailField label="Company" value={contractor?.company} />
              <DetailField label="Phone" value={contractor?.phone} />
              <DetailField label="Billing Entity" value={contractor?.billing_entity} />
              <DetailField label="Status" value={contractor?.is_active ? "Active" : "Disabled"} />
            </div>
          </DetailSection>

          <DetailSection label="Timestamps">
            <div className="grid grid-cols-2 gap-4">
              <DetailField
                label="Created"
                value={
                  contractor?.created_at
                    ? format(new Date(contractor.created_at), "MMM d, yyyy h:mm a")
                    : undefined
                }
              />
              <DetailField
                label="Last Login"
                value={
                  contractor?.last_login
                    ? format(new Date(contractor.last_login), "MMM d, yyyy h:mm a")
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
