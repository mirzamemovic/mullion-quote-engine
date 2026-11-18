/** Server state through TanStack Query: one hook per thing the screens read or change. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, get, getFile, patch, post, put } from "./client";
import type {
  Calculation,
  Client,
  ClientIn,
  Colour,
  Me,
  Measure,
  Payment,
  PriceList,
  ProfileSystem,
  QuoteDetail,
  QuoteSummary,
  RevisionIn,
  Settings,
  Supplier,
} from "./types";

export const keys = {
  me: ["me"] as const,
  quotes: (search: string, status: string) => ["quotes", search, status] as const,
  quote: (id: string) => ["quote", id] as const,
  calculation: (id: string, revision: number) => ["calculation", id, revision] as const,
  clients: (search: string) => ["clients", search] as const,
  systems: ["systems"] as const,
  priceLists: ["price-lists"] as const,
  suppliers: ["suppliers"] as const,
  settings: ["settings"] as const,
  payments: (id: string) => ["payments", id] as const,
};

/** The logged-in user, or ``null`` when nobody is logged in. */
export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: async (): Promise<Me | null> => {
      try {
        return await get<Me>("/auth/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          return null;
        }
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) => post<Me>("/auth/login", body),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

export function useTotp() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => post<Me>("/auth/totp", { code }),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

export function useReauth() {
  return useMutation({
    mutationFn: (password: string) => post<Me>("/auth/reauth", { password }),
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => post<undefined>("/auth/logout"),
    onSettled: () => {
      client.clear();
      client.setQueryData(keys.me, null);
    },
  });
}

export function useQuotes(search: string, status: string) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (status) params.set("status_filter", status);
  const query = params.toString();
  return useQuery({
    queryKey: keys.quotes(search, status),
    queryFn: () => get<QuoteSummary[]>(`/quotes${query ? `?${query}` : ""}`),
  });
}

export function useQuote(id: string) {
  return useQuery({ queryKey: keys.quote(id), queryFn: () => get<QuoteDetail>(`/quotes/${id}`) });
}

export function useCalculation(id: string, revision: number, enabled: boolean) {
  return useQuery({
    queryKey: keys.calculation(id, revision),
    queryFn: () => post<Calculation>(`/quotes/${id}/revisions/${revision}/calculate`),
    enabled,
    retry: false,
  });
}

export type DocumentKind = "quote" | "workshop";
export type DocumentLanguage = "en" | "bs";

/** A revision's client quote or workshop sheet as a PDF file. */
export function useDocument(id: string, revision: number) {
  return useMutation({
    mutationFn: ({ kind, lang }: { kind: DocumentKind; lang: DocumentLanguage }) =>
      getFile(`/quotes/${id}/revisions/${revision}/${kind}.pdf?lang=${lang}`, `${kind}.pdf`),
  });
}

export function useClients(search: string) {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  return useQuery({ queryKey: keys.clients(search), queryFn: () => get<Client[]>(`/clients${query}`) });
}

export function useCreateClient() {
  return useMutation({ mutationFn: (body: ClientIn) => post<Client>("/clients", body) });
}

export function useSystems() {
  return useQuery({ queryKey: keys.systems, queryFn: () => get<ProfileSystem[]>("/systems") });
}

export function useCreateQuote() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { client_id: string; profile_system_id: string }) =>
      post<QuoteDetail>("/quotes", body),
    onSuccess: (quote) => {
      client.setQueryData(keys.quote(quote.id), quote);
      void client.invalidateQueries({ queryKey: ["quotes"] });
    },
  });
}

export function useSaveRevision(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ revision, body }: { revision: number; body: RevisionIn }) =>
      put<QuoteDetail>(`/quotes/${id}/revisions/${revision}`, body),
    onSuccess: (quote) => {
      client.setQueryData(keys.quote(id), quote);
      void client.invalidateQueries({ queryKey: ["calculation", id] });
      void client.invalidateQueries({ queryKey: ["quotes"] });
    },
  });
}

export function useNewRevision(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => post<QuoteDetail>(`/quotes/${id}/revisions`),
    onSuccess: (quote) => client.setQueryData(keys.quote(id), quote),
  });
}

export function useSetStatus(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (status: "draft" | "sent" | "accepted" | "rejected") =>
      post<QuoteDetail>(`/quotes/${id}/status`, { status }),
    onSuccess: (quote) => {
      client.setQueryData(keys.quote(id), quote);
      void client.invalidateQueries({ queryKey: ["quotes"] });
      void client.invalidateQueries({ queryKey: ["calculation", id] });
    },
  });
}

export function usePayments(id: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.payments(id),
    queryFn: () => get<Payment[]>(`/quotes/${id}/payments`),
    enabled,
  });
}

export function useAddPayment(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { kind: "advance" | "balance"; amount_cents: number; received_on: string }) =>
      post<Payment>(`/quotes/${id}/payments`, body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: keys.payments(id) });
      void client.invalidateQueries({ queryKey: keys.quote(id) });
    },
  });
}

export function useMeasure() {
  return useMutation({
    mutationFn: (body: { readings: { widths: number[]; heights: number[] }; colour: Colour }) =>
      post<Measure>("/engine/measure", body),
  });
}

export function usePriceLists() {
  return useQuery({ queryKey: keys.priceLists, queryFn: () => get<PriceList[]>("/price-lists") });
}

export function useSuppliers() {
  return useQuery({ queryKey: keys.suppliers, queryFn: () => get<Supplier[]>("/suppliers") });
}

export function useBump() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ listId, body }: { listId: string; body: { supplier_id: string; bp: number; valid_from: string } }) =>
      post<PriceList>(`/price-lists/${listId}/bump`, body),
    onSuccess: () => void client.invalidateQueries({ queryKey: keys.priceLists }),
  });
}

export function useSettings() {
  return useQuery({ queryKey: keys.settings, queryFn: () => get<Settings>("/settings") });
}

export function useSaveSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Settings) => put<Settings>("/settings", body),
    onSuccess: (saved) => client.setQueryData(keys.settings, saved),
  });
}

export function useUpdateSupplier() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Omit<Supplier, "id"> }) =>
      patch<Supplier>(`/suppliers/${id}`, body),
    onSuccess: () => void client.invalidateQueries({ queryKey: keys.suppliers }),
  });
}
