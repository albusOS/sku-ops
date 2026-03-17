import { useQueryClient, useMutation } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { createEntityHooks } from "./useEntityHooks";
import { keys } from "./queryKeys";

const { useList, useDetail } = createEntityHooks("returns", api.returns);

export function useReturns(params) {
  return useList(params);
}

export function useReturn(id) {
  return useDetail(id);
}

export function useCreateReturn(options = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => api.returns.create(data),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: keys.returns.all });
      qc.invalidateQueries({ queryKey: keys.withdrawals.all });
      qc.invalidateQueries({ queryKey: ["reports"] });
      options.onSuccess?.(...args);
    },
  });
}
