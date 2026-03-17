import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { FileText } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import { PendingRequestsSection } from "@/components/operations/PendingRequestsSection";
import { UninvoicedWithdrawalsSection } from "@/components/operations/UninvoicedWithdrawalsSection";
import { IssueMaterialsCTA } from "@/components/operations/IssueMaterialsCTA";
import { useMaterialRequests, useProcessMaterialRequest } from "@/hooks/useMaterialRequests";
import { getErrorMessage } from "@/lib/api-client";
import { dateToISO, endOfDayISO } from "@/lib/utils";
import { DATE_PRESETS } from "@/lib/constants";

const OperationsHub = () => {
  const defaultRange = DATE_PRESETS[1].getValue();
  const [dateRange, setDateRange] = useState(defaultRange);

  const dateParams = useMemo(
    () => ({
      start_date: dateToISO(dateRange.from),
      end_date: endOfDayISO(dateRange.to),
    }),
    [dateRange],
  );

  const {
    data: allRequests,
    isLoading: requestsLoading,
    isError: requestsError,
    error: _requestsErr,
    refetch: refetchRequests,
  } = useMaterialRequests(undefined, { refetchInterval: 30000 });
  const processRequest = useProcessMaterialRequest();

  const requests = (allRequests || []).filter((r) => r.status === "pending");

  const handleProcess = async (requestId, data) => {
    try {
      await processRequest.mutateAsync({ id: requestId, data });
      toast.success("Request processed. Withdrawal created.");
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    }
  };

  const handleInvoiceCreated = (inv) => {
    if (inv?.id) {
      // Optionally navigate to invoices or open InvoiceDetailModal
      // For now we rely on UninvoicedWithdrawalsSection to handle it
    }
  };

  return (
    <div className="p-8" data-testid="operations-hub-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Issue Materials</h1>
          <p className="text-muted-foreground mt-1 text-sm">Issue materials and create invoices</p>
        </div>
        <Link to="/invoices">
          <Button variant="outline" size="sm" className="gap-2">
            <FileText className="w-4 h-4" />
            View Invoices
          </Button>
        </Link>
      </div>

      {/* To Issue */}
      <section className="mb-10">
        <h2 className="text-base font-semibold text-foreground mb-4">To Issue</h2>
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="flex-1">
            <PendingRequestsSection
              requests={requests}
              isLoading={requestsLoading}
              error={requestsError ? _requestsErr : null}
              onRetry={refetchRequests}
              onProcess={handleProcess}
              isProcessing={processRequest.isPending}
            />
          </div>
          <div className="lg:w-64 shrink-0">
            <IssueMaterialsCTA />
          </div>
        </div>
      </section>

      {/* To Invoice */}
      <section>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <h2 className="text-base font-semibold text-foreground">To Invoice</h2>
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
        </div>
        <UninvoicedWithdrawalsSection
          dateParams={dateParams}
          onViewInvoice={() => {}}
          onCreateInvoice={handleInvoiceCreated}
        />
      </section>
    </div>
  );
};

export default OperationsHub;
