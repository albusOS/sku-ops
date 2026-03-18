import api from "@/lib/api-client";
import { createEntityHooks } from "./useEntityHooks";

const { useList, useDetail, useCreate, useUpdate } = createEntityHooks(
  "billingEntities",
  api.billingEntities,
);

export { useCreate as useCreateBillingEntity, useUpdate as useUpdateBillingEntity };

export function useBillingEntities(params) {
  return useList(params);
}

export function useBillingEntity(id) {
  return useDetail(id);
}
