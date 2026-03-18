import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { createEntityHooks } from "./useEntityHooks";
import { keys } from "./queryKeys";

const { useList, useCreate, useUpdate, useDelete } = createEntityHooks("products", api.products);

export {
  useCreate as useCreateProduct,
  useUpdate as useUpdateProduct,
  useDelete as useDeleteProduct,
};

export function useProducts(params) {
  return useList(params);
}

export function useStockHistory(productId) {
  return useQuery({
    queryKey: keys.products.stockHistory(productId),
    queryFn: () => api.products.stockHistory(productId),
    enabled: !!productId,
  });
}

export function useAdjustStock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => api.products.adjust(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.products.all }),
  });
}

export function useSuggestUom() {
  return useMutation({
    mutationFn: (data) => api.products.suggestUom(data),
  });
}

export function useVendorItems(skuId) {
  return useQuery({
    queryKey: [...keys.products.all, "vendorItems", skuId],
    queryFn: () => api.catalog.vendorItems.list(skuId),
    enabled: !!skuId,
  });
}

export function useAddVendorItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ skuId, data }) => api.catalog.vendorItems.create(skuId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.products.all }),
  });
}

export function useRemoveVendorItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ skuId, itemId }) => api.catalog.vendorItems.delete(skuId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.products.all }),
  });
}

export function useSetPreferredVendor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ skuId, itemId }) => api.catalog.vendorItems.setPreferred(skuId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.products.all }),
  });
}

export function useProductFamily(familyId) {
  return useQuery({
    queryKey: keys.productFamilies.detail(familyId),
    queryFn: () => api.productFamilies.get(familyId),
    enabled: !!familyId,
  });
}

export function useCreateVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ familyId, data }) => api.productFamilies.createSku(familyId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.products.all });
      qc.invalidateQueries({ queryKey: keys.productFamilies.all });
    },
  });
}
