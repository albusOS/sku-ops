import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { createEntityHooks } from "./useEntityHooks";
import { keys } from "./queryKeys";

const { useList, useCreate, useUpdate, useDelete } = createEntityHooks(
  "departments",
  api.departments,
);

export {
  useCreate as useCreateDepartment,
  useUpdate as useUpdateDepartment,
  useDelete as useDeleteDepartment,
  useCreate as useCreateCategory,
  useUpdate as useUpdateCategory,
  useDelete as useDeleteCategory,
};

export function useDepartments() {
  return useList();
}

export const useCategories = useDepartments;

export function useSkuOverview() {
  return useQuery({
    queryKey: keys.departments.skuOverview(),
    queryFn: () => api.sku.overview().catch(() => null),
  });
}
