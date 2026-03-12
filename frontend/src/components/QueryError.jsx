import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Full-page error state for failed queries. Shows a retry button.
 * Use in place of <PageSkeleton /> when isError is true.
 */
export function QueryError({ error, onRetry, className = "" }) {
  const isNetwork = !error?.response;
  const status = error?.response?.status;
  const message = isNetwork
    ? "Could not reach the server. Check your connection and try again."
    : status >= 500
      ? "Something went wrong on the server. Try again in a moment."
      : error?.response?.data?.detail || "Failed to load data.";

  return (
    <div className={`flex flex-col items-center justify-center py-24 px-8 ${className}`}>
      {isNetwork ? (
        <WifiOff className="w-12 h-12 text-muted-foreground/50 mb-4" />
      ) : (
        <AlertTriangle className="w-12 h-12 text-destructive/60 mb-4" />
      )}
      <p className="text-sm text-muted-foreground text-center max-w-md mb-6">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Try again
        </Button>
      )}
    </div>
  );
}
