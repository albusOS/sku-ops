import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { keys } from "./queryKeys";

const REPORT_STALE = 30_000;
const REPORT_REFETCH = 120_000;
const reportOpts = { staleTime: REPORT_STALE, refetchInterval: REPORT_REFETCH };

export function useReportSales(params) {
  return useQuery({
    queryKey: keys.reports.sales(params),
    queryFn: () => api.reports.sales(params),
    enabled: !!params,
    ...reportOpts,
  });
}

export function useReportInventory() {
  return useQuery({
    queryKey: keys.reports.inventory(),
    queryFn: api.reports.inventory,
    ...reportOpts,
  });
}

export function useReportTrends(params) {
  return useQuery({
    queryKey: keys.reports.trends(params),
    queryFn: () => api.reports.trends(params),
    enabled: !!params,
    ...reportOpts,
  });
}

export function useReportMargins(params) {
  return useQuery({
    queryKey: keys.reports.productMargins(params),
    queryFn: () => api.reports.productMargins(params),
    enabled: !!params,
    ...reportOpts,
  });
}

export function useReportPL(params) {
  return useQuery({
    queryKey: keys.reports.pl(params),
    queryFn: () => api.reports.pl(params),
    enabled: !!params,
    ...reportOpts,
  });
}

export function useReportArAging(params) {
  return useQuery({
    queryKey: keys.reports.arAging(params),
    queryFn: () => (params ? api.reports.arAging(params) : api.reports.arAging()),
    ...reportOpts,
  });
}

export function useReportKpis(params) {
  return useQuery({
    queryKey: keys.reports.kpis(params),
    queryFn: () => api.reports.kpis(params),
    enabled: !!params,
    ...reportOpts,
  });
}

export function useReportProductPerformance(params) {
  return useQuery({
    queryKey: keys.reports.productPerformance(params),
    queryFn: () => api.reports.productPerformance(params),
    enabled: !!params,
    ...reportOpts,
  });
}

export function useReportJobPl(params) {
  return useQuery({
    queryKey: keys.reports.jobPl(params),
    queryFn: () => api.reports.jobPl(params),
    enabled: !!params,
    ...reportOpts,
  });
}

export function useReportReorderUrgency(params) {
  return useQuery({
    queryKey: keys.reports.reorderUrgency(params),
    queryFn: () => api.reports.reorderUrgency(params),
    ...reportOpts,
  });
}

export function useReportProductActivity(params) {
  return useQuery({
    queryKey: keys.reports.productActivity(params),
    queryFn: () => api.reports.productActivity(params),
    enabled: params !== false,
    ...reportOpts,
  });
}
