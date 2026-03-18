import api from "@/lib/api-client";
import { createEntityHooks } from "./useEntityHooks";

const { useList, useCreate, useDelete } = createEntityHooks("units", api.units);

export { useCreate as useCreateUnit, useDelete as useDeleteUnit };

export function useUnitsOfMeasure() {
  return useList();
}
