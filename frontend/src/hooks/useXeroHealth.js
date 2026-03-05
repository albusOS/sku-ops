import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { keys } from "./queryKeys";

export function useXeroHealth() {
  return useQuery({
    queryKey: keys.xeroHealth.summary(),
    queryFn: api.xero.health,
    staleTime: 30_000,
  });
}

export function useTriggerXeroSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.xero.triggerSync,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.xeroHealth.all });
    },
  });
}
