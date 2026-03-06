import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { keys } from "./queryKeys";

export function useReportSales(params) {
  return useQuery({
    queryKey: keys.reports.sales(params),
    queryFn: () => api.reports.sales(params),
    enabled: !!params,
  });
}

export function useReportInventory() {
  return useQuery({
    queryKey: keys.reports.inventory(),
    queryFn: api.reports.inventory,
  });
}

export function useReportTrends(params) {
  return useQuery({
    queryKey: keys.reports.trends(params),
    queryFn: () => api.reports.trends(params),
    enabled: !!params,
  });
}

export function useReportMargins(params) {
  return useQuery({
    queryKey: keys.reports.productMargins(params),
    queryFn: () => api.reports.productMargins(params),
    enabled: !!params,
  });
}

export function useReportPL(params) {
  return useQuery({
    queryKey: keys.reports.pl(params),
    queryFn: () => api.reports.pl(params),
    enabled: !!params,
  });
}

export function useReportArAging(params) {
  return useQuery({
    queryKey: keys.reports.arAging(params),
    queryFn: () => params ? api.reports.arAging(params) : api.reports.arAging(),
  });
}

export function useReportKpis(params) {
  return useQuery({
    queryKey: keys.reports.kpis(params),
    queryFn: () => api.reports.kpis(params),
    enabled: !!params,
  });
}

export function useReportProductPerformance(params) {
  return useQuery({
    queryKey: keys.reports.productPerformance(params),
    queryFn: () => api.reports.productPerformance(params),
    enabled: !!params,
  });
}

export function useReportJobPl(params) {
  return useQuery({
    queryKey: keys.reports.jobPl(params),
    queryFn: () => api.reports.jobPl(params),
    enabled: !!params,
  });
}

export function useReportReorderUrgency(params) {
  return useQuery({
    queryKey: keys.reports.reorderUrgency(params),
    queryFn: () => api.reports.reorderUrgency(params),
  });
}

export function useReportProductActivity(params) {
  return useQuery({
    queryKey: keys.reports.productActivity(params),
    queryFn: () => api.reports.productActivity(params),
    enabled: params !== false,
  });
}
