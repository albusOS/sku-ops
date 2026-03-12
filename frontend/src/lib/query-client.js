import { QueryClient, MutationCache, QueryCache } from "@tanstack/react-query";
import { toast } from "sonner";
import { getErrorMessage } from "./api-client";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      const status = error?.response?.status;
      // Auth errors are handled by the auth context — no toast needed
      if (status === 401 || status === 403) return;
      // Queries that opt out of the global error toast
      if (query.options.meta?.silentError) return;
      // Only show once per query key (not on every background refetch failure)
      if (query.state.dataUpdatedAt === 0) {
        toast.error(getErrorMessage(error));
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      const status = error?.response?.status;
      if (status === 401 || status === 403) return;
      // Always show a toast — local onError handlers can do additional work
      // but the user should always see feedback when a mutation fails.
      if (mutation.options.meta?.silentError) return;
      toast.error(getErrorMessage(error));
    },
  }),
});
