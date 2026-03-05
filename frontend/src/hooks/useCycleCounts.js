import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { keys } from "./queryKeys";

export function useCycleCounts(params) {
  return useQuery({
    queryKey: keys.cycleCounts.list(params),
    queryFn: () => api.cycleCounts.list(params),
  });
}

export function useCycleCount(id) {
  return useQuery({
    queryKey: keys.cycleCounts.detail(id),
    queryFn: () => api.cycleCounts.get(id),
    enabled: !!id,
  });
}

export function useOpenCycleCount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => api.cycleCounts.open(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.cycleCounts.all }),
  });
}

export function useUpdateCountItem(countId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, data }) => api.cycleCounts.updateItem(countId, itemId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.cycleCounts.detail(countId) }),
  });
}

export function useCommitCycleCount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => api.cycleCounts.commit(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.cycleCounts.all });
      qc.invalidateQueries({ queryKey: keys.products.all });
    },
  });
}
