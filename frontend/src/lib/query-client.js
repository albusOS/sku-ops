import { QueryClient, MutationCache } from "@tanstack/react-query";
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
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      const status = error?.response?.status;
      if (status === 401 || status === 403) return;
      if (mutation.options.onError) return;
      toast.error(getErrorMessage(error));
    },
  }),
});
