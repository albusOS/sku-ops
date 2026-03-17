import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { HardHat, Package, Clock, AlertTriangle } from "lucide-react";
import { QueryError } from "@/components/QueryError";
import { ProcessRequestModal } from "./ProcessRequestModal";
import { getErrorMessage } from "@/lib/api-client";

function ageLabel(dateStr) {
  const mins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function ageHours(dateStr) {
  return (Date.now() - new Date(dateStr).getTime()) / 3600000;
}

export function PendingRequestsSection({
  requests,
  isLoading,
  error,
  onRetry,
  onProcess,
  isProcessing,
}) {
  const [processOpen, setProcessOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [jobId, setJobId] = useState("");
  const [serviceAddress, setServiceAddress] = useState("");
  const [notes, setNotes] = useState("");

  const sorted = [...(requests || [])].sort(
    (a, b) => new Date(a.created_at) - new Date(b.created_at),
  );
  const oldestRequest = sorted[0];

  const openProcess = (req) => {
    setSelectedRequest(req);
    setJobId(req.job_id || "");
    setServiceAddress(req.service_address || "");
    setNotes(req.notes || "");
    setProcessOpen(true);
  };

  const closeProcess = () => {
    setProcessOpen(false);
    setSelectedRequest(null);
    setJobId("");
    setServiceAddress("");
    setNotes("");
  };

  const handleProcess = async () => {
    if (!selectedRequest || !jobId.trim() || !serviceAddress.trim()) return;
    try {
      await onProcess(selectedRequest.id, {
        job_id: jobId.trim(),
        service_address: serviceAddress.trim(),
        notes: notes.trim() || null,
      });
      toast.success("Request processed. Withdrawal created.");
      closeProcess();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  if (error) return <QueryError error={error} onRetry={onRetry} />;

  return (
    <>
      <div className="flex flex-col gap-3 mb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground">Pending requests</h3>
          <p className="text-sm text-muted-foreground">
            Submitted contractor requests waiting to be turned into withdrawals.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 md:min-w-[240px]">
          <div className="rounded-xl border border-border/60 bg-muted/30 px-3 py-2.5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
              Queue
            </p>
            <p className="mt-1 text-lg font-semibold text-foreground">{sorted.length}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-muted/30 px-3 py-2.5">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
              Oldest
            </p>
            <p className="mt-1 text-lg font-semibold text-foreground">
              {oldestRequest ? ageLabel(oldestRequest.created_at) : "None"}
            </p>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="bg-card border border-border rounded-xl p-12 text-center min-h-[280px] flex items-center justify-center">
          <p className="text-sm text-muted-foreground">Loading requests…</p>
        </div>
      ) : sorted.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-16 text-center shadow-sm min-h-[280px] flex flex-col items-center justify-center">
          <Package className="w-12 h-12 mx-auto text-muted-foreground/60 mb-3" />
          <p className="font-medium text-muted-foreground">No pending requests</p>
          <p className="text-sm text-muted-foreground mt-1">
            Requests will appear here when contractors submit them.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sorted.map((req) => {
            const hours = ageHours(req.created_at);
            const border =
              hours >= 48
                ? "border-destructive/30 bg-destructive/10"
                : hours >= 24
                  ? "border-warning/30 bg-warning/10"
                  : "border-border";
            const ageCls =
              hours >= 48
                ? "text-destructive bg-destructive/10"
                : hours >= 24
                  ? "text-category-5 bg-warning/10"
                  : "text-muted-foreground";
            const itemCount = (req.items || []).reduce((s, i) => s + (i.quantity || 0), 0);
            return (
              <div
                key={req.id}
                className={`bg-card border rounded-xl p-5 shadow-sm h-full ${border}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center shrink-0">
                      <HardHat className="w-5 h-5 text-accent" />
                    </div>
                    <div>
                      <p className="font-semibold text-foreground text-sm">
                        {req.contractor_name || "Unknown"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {itemCount} item{itemCount !== 1 ? "s" : ""}
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={() => openProcess(req)}
                    size="sm"
                    data-testid={`process-request-${req.id}`}
                  >
                    Process
                  </Button>
                </div>
                {req.items?.length > 0 && (
                  <div className="border-t border-border/50 pt-3 mb-3">
                    <ul className="space-y-0.5 text-xs text-muted-foreground">
                      {req.items.map((i, idx) => (
                        <li key={idx} className="flex justify-between">
                          <span className="truncate">{i.name}</span>
                          <span className="font-mono text-muted-foreground ml-2 shrink-0">
                            x{i.quantity}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(req.created_at).toLocaleDateString()}
                  </span>
                  <span
                    className={`font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 ${ageCls}`}
                  >
                    {hours >= 24 && <AlertTriangle className="w-3 h-3" />}
                    {ageLabel(req.created_at)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <ProcessRequestModal
        open={processOpen}
        onOpenChange={(open) => !open && closeProcess()}
        request={selectedRequest}
        jobId={jobId}
        onJobIdChange={setJobId}
        serviceAddress={serviceAddress}
        onServiceAddressChange={setServiceAddress}
        notes={notes}
        onNotesChange={setNotes}
        onSubmit={handleProcess}
        isPending={isProcessing}
      />
    </>
  );
}
