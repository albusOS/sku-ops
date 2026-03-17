import { RotateCcw, HardHat, Briefcase, Building2, FileText, User } from "lucide-react";
import { format } from "date-fns";
import { DetailPanel, DetailSection, DetailField } from "../DetailPanel";
import { StatusBadge } from "../StatusBadge";
import { useReturn } from "@/hooks/useReturns";

const REASON_LABELS = {
  wrong_item: "Wrong Item",
  defective: "Defective",
  overorder: "Over-ordered",
  job_cancelled: "Job Cancelled",
  other: "Other",
};

export function ReturnDetailPanel({ returnId, open, onOpenChange }) {
  const { data: ret, isLoading } = useReturn(open ? returnId : null);

  const items = ret?.items || [];

  return (
    <DetailPanel
      open={open}
      onOpenChange={onOpenChange}
      title="Return Detail"
      subtitle={ret?.id ? ret.id.slice(0, 12) + "…" : undefined}
      icon={RotateCcw}
      loading={isLoading}
      width="lg"
    >
      <DetailSection label="Details">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Contractor</p>
            <div className="flex items-center gap-2 mt-1">
              <HardHat className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">
                {ret?.contractor_name || "—"}
              </span>
            </div>
          </div>
          <DetailField
            label="Date"
            value={
              ret?.created_at ? format(new Date(ret.created_at), "MMM d, yyyy h:mm a") : undefined
            }
          />
          <div>
            <p className="text-xs text-muted-foreground">Job</p>
            {ret?.job_id ? (
              <div className="text-sm font-mono text-info mt-0.5 flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5" />
                {ret.job_id}
              </div>
            ) : (
              <p className="text-sm text-foreground mt-0.5">—</p>
            )}
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Billing Entity</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-sm text-foreground">{ret?.billing_entity || "—"}</span>
            </div>
          </div>
          <DetailField label="Reason" value={REASON_LABELS[ret?.reason] || ret?.reason || "—"} />
          <div>
            <p className="text-xs text-muted-foreground">Processed By</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <User className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-sm text-foreground">{ret?.processed_by_name || "—"}</span>
            </div>
          </div>
        </div>
      </DetailSection>

      {ret?.credit_note_id && (
        <DetailSection label="Credit Note">
          <div className="flex items-center gap-2 text-sm">
            <FileText className="w-4 h-4 text-muted-foreground" />
            <span className="font-mono text-xs text-foreground">
              {ret.credit_note_id.slice(0, 12)}…
            </span>
            <StatusBadge status="approved" />
          </div>
        </DetailSection>
      )}

      <DetailSection label="Returned Items">
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/80 border-b border-border">
                <th className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Item
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider w-14">
                  Qty
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider w-20">
                  Unit $
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider w-20">
                  Cost
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider w-20">
                  Refund
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx} className="border-b border-border/50 last:border-b-0">
                  <td className="px-3 py-2">
                    <p className="font-medium text-foreground">{item.name || "—"}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {item.sku && (
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {item.sku}
                        </span>
                      )}
                      {item.reason && item.reason !== "other" && (
                        <span className="text-[10px] text-warning capitalize">
                          {item.reason.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-muted-foreground">
                    {item.quantity}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-muted-foreground">
                    ${(item.unit_price ?? 0).toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-muted-foreground">
                    ${(item.cost ?? 0).toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-semibold text-destructive">
                    ${((item.quantity ?? 0) * (item.unit_price ?? 0)).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex justify-end mt-3 gap-6">
          <div className="text-right">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Cost Recovered</p>
            <p className="text-sm font-semibold font-mono text-success">
              ${(ret?.cost_total ?? 0).toFixed(2)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Subtotal</p>
            <p className="text-sm font-semibold font-mono text-foreground">
              ${(ret?.subtotal ?? 0).toFixed(2)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Tax</p>
            <p className="text-sm font-semibold font-mono text-muted-foreground">
              ${(ret?.tax ?? 0).toFixed(2)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Total Refund</p>
            <p className="text-sm font-bold font-mono text-destructive">
              ${(ret?.total ?? 0).toFixed(2)}
            </p>
          </div>
        </div>
      </DetailSection>

      {ret?.notes && (
        <DetailSection label="Notes">
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{ret.notes}</p>
        </DetailSection>
      )}
    </DetailPanel>
  );
}
