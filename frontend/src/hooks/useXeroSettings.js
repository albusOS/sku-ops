import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { keys } from "./queryKeys";

export function useXeroSettings() {
  return useQuery({
    queryKey: keys.settings.xero(),
    queryFn: api.settings.xero,
    staleTime: 60_000,
  });
}

export function useUpdateXeroSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.settings.updateXero,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.settings.all }),
  });
}

export function useXeroTenants(enabled = false) {
  return useQuery({
    queryKey: ["xero", "tenants"],
    queryFn: api.xero.tenants,
    enabled,
    staleTime: 120_000,
  });
}

export function useXeroTrackingCategories(enabled = false) {
  return useQuery({
    queryKey: ["xero", "trackingCategories"],
    queryFn: api.xero.trackingCategories,
    enabled,
    staleTime: 120_000,
  });
}

export function useXeroDisconnect() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.xero.disconnect,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.settings.all }),
  });
}

export function useSelectTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.xero.selectTenant,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.settings.all }),
  });
}

export function useSelectTrackingCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.xero.selectTrackingCategory,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.settings.all }),
  });
}
