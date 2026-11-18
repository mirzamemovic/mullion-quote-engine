/**
 * Hooks for running a workshop: the setup checklist, profile systems and their sheets, prices,
 * suppliers, the team, the workshop profile, and the person's own login. Joining and "Try it"
 * live here too, because they open a session like a login does.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { del, get, patch, post, put } from "./client";
import { keys } from "./queries";
import type {
  ConstructionTypeState,
  HardwareSet,
  HardwareSetIn,
  Invite,
  InviteCreated,
  InviteInfo,
  Me,
  PriceEntryIn,
  PriceList,
  ProfileSystem,
  ProfileSystemIn,
  Role,
  SessionRow,
  SetupStatus,
  Sheet,
  SheetFields,
  Supplier,
  TotpSetup,
  User,
  Workshop,
} from "./types";

export const workshopKeys = {
  setup: (priceList?: string) => ["setup", priceList ?? "current"] as const,
  sheets: (system: string) => ["sheets", system] as const,
  sheetFields: (system: string, reinforced: boolean) => ["sheet-fields", system, reinforced] as const,
  priceList: (id: string) => ["price-list", id] as const,
  hardware: ["hardware-sets"] as const,
  types: ["construction-types"] as const,
  users: ["users"] as const,
  sessions: ["sessions"] as const,
  invites: ["invites"] as const,
  workshop: ["workshop"] as const,
};

/** Everything that depends on the catalogue or prices is refreshed after a change. */
function useRefresh() {
  const client = useQueryClient();
  return () => {
    for (const key of ["setup", "price-lists", "price-list", "systems", "sheets", "sheet-fields", "hardware-sets", "construction-types"]) {
      void client.invalidateQueries({ queryKey: [key] });
    }
  };
}

// --- ways in ------------------------------------------------------------------------------------

export function useStartSandbox() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (language: "en" | "bs") => post<Me>("/sandbox", { language }),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

export function useInviteInfo(token: string) {
  return useQuery({
    queryKey: ["invite", token],
    queryFn: () => post<InviteInfo>("/join/info", { token }),
    enabled: token.length >= 20,
    retry: false,
  });
}

export function useJoin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { token: string; email: string; password: string }) => post<Me>("/join", body),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

// --- setup checklist ----------------------------------------------------------------------------

export function useSetupStatus(priceListId?: string) {
  const query = priceListId ? `?price_list_id=${priceListId}` : "";
  return useQuery({
    queryKey: workshopKeys.setup(priceListId),
    queryFn: () => get<SetupStatus>(`/setup/status${query}`),
  });
}

export function useStarterPrices() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (withSystems: boolean) => post<PriceList>("/setup/starter-prices", { with_systems: withSystems }),
    onSuccess: refresh,
  });
}

// --- profile systems, sheets, hardware, construction types --------------------------------------

export function useCreateSystem() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (body: ProfileSystemIn) => post<ProfileSystem>("/systems", body), onSuccess: refresh });
}

export function useSheets(systemId: string) {
  return useQuery({ queryKey: workshopKeys.sheets(systemId), queryFn: () => get<Sheet[]>(`/systems/${systemId}/sheets`) });
}

export function useSheetFields(systemId: string, reinforced: boolean) {
  return useQuery({
    queryKey: workshopKeys.sheetFields(systemId, reinforced),
    queryFn: () => get<SheetFields>(`/systems/${systemId}/sheet-fields?reinforced=${reinforced}`),
  });
}

export function useSaveSheetDraft(systemId: string) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: { constants: Record<string, unknown>; source_pages: Record<string, string> }) =>
      post<Sheet>(`/systems/${systemId}/sheets/draft`, body),
    onSuccess: refresh,
  });
}

export function usePublishSheet(systemId: string) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (version: number) => post<Sheet>(`/systems/${systemId}/sheets/${version}/publish`),
    onSuccess: refresh,
  });
}

export function useCutPreview() {
  return useMutation({
    mutationFn: (body: { constants: Record<string, unknown>; construction_type: string; width_mm: number; height_mm: number }) =>
      post<{ cut_list: import("./types").CutList }>("/engine/cut-preview", body),
  });
}

export function useHardwareSets() {
  return useQuery({ queryKey: workshopKeys.hardware, queryFn: () => get<HardwareSet[]>("/hardware-sets") });
}

export function useAddHardwareSet() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (body: HardwareSetIn) => post<HardwareSet>("/hardware-sets", body), onSuccess: refresh });
}

export function useDeleteHardwareSet() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (id: string) => del<undefined>(`/hardware-sets/${id}`), onSuccess: refresh });
}

export function useConstructionTypes() {
  return useQuery({ queryKey: workshopKeys.types, queryFn: () => get<ConstructionTypeState[]>("/construction-types") });
}

export function useSetConstructionType() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: ConstructionTypeState) => put<ConstructionTypeState>("/construction-types", body),
    onSuccess: refresh,
  });
}

// --- prices and suppliers -----------------------------------------------------------------------

export function usePriceList(id: string) {
  return useQuery({ queryKey: workshopKeys.priceList(id), queryFn: () => get<PriceList>(`/price-lists/${id}`) });
}

export function useNewDraft() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: { copy_from?: string; note?: string }) => post<PriceList>("/price-lists/drafts", body),
    onSuccess: refresh,
  });
}

export function useSaveEntries(id: string) {
  const client = useQueryClient();
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (entries: PriceEntryIn[]) => put<PriceList>(`/price-lists/${id}/entries`, { entries }),
    onSuccess: (saved) => {
      client.setQueryData(workshopKeys.priceList(id), saved);
      refresh();
    },
  });
}

export function useImportCsv(id: string) {
  const client = useQueryClient();
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (contentBase64: string) => post<PriceList>(`/price-lists/${id}/csv`, { content_base64: contentBase64 }),
    onSuccess: (saved) => {
      client.setQueryData(workshopKeys.priceList(id), saved);
      refresh();
    },
  });
}

export function usePublishPriceList(id: string) {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (validFrom: string) => post<PriceList>(`/price-lists/${id}/publish`, { valid_from: validFrom }),
    onSuccess: refresh,
  });
}

export function useDeleteDraft() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (id: string) => del<undefined>(`/price-lists/${id}`), onSuccess: refresh });
}

export function useAddSupplier() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Omit<Supplier, "id">) => post<Supplier>("/suppliers", body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: keys.suppliers });
      void client.invalidateQueries({ queryKey: ["setup"] });
    },
  });
}

// --- the team -----------------------------------------------------------------------------------

export function useUsers() {
  return useQuery({ queryKey: workshopKeys.users, queryFn: () => get<User[]>("/users") });
}

export function useChangeUser() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { is_active?: boolean; role?: Role } }) => patch<User>(`/users/${id}`, body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: workshopKeys.users });
      void client.invalidateQueries({ queryKey: workshopKeys.sessions });
    },
  });
}

export function useSessions() {
  return useQuery({ queryKey: workshopKeys.sessions, queryFn: () => get<SessionRow[]>("/sessions") });
}

export function useRevokeSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => del<undefined>(`/sessions/${id}`),
    onSuccess: () => void client.invalidateQueries({ queryKey: workshopKeys.sessions }),
  });
}

export function useInvites() {
  return useQuery({ queryKey: workshopKeys.invites, queryFn: () => get<Invite[]>("/invites") });
}

export function useCreateInvite() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (role: Role) => post<InviteCreated>("/invites", { role }),
    onSuccess: () => void client.invalidateQueries({ queryKey: workshopKeys.invites }),
  });
}

export function useRevokeInvite() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => del<undefined>(`/invites/${id}`),
    onSuccess: () => void client.invalidateQueries({ queryKey: workshopKeys.invites }),
  });
}

// --- the workshop profile and the person's own login --------------------------------------------

export function useWorkshop() {
  return useQuery({ queryKey: workshopKeys.workshop, queryFn: () => get<Workshop>("/workshop") });
}

export function useSaveWorkshop() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Workshop) => put<Workshop>("/workshop", body),
    onSuccess: (saved) => {
      client.setQueryData(workshopKeys.workshop, saved);
      void client.invalidateQueries({ queryKey: keys.me });
    },
  });
}

/** The logo on client PDFs: a PNG or JPEG of at most 300 KB, sent as base64. */
export function useSaveLogo() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (contentBase64: string) => put<Workshop>("/workshop/logo", { content_base64: contentBase64 }),
    onSuccess: (saved) => client.setQueryData(workshopKeys.workshop, saved),
  });
}

export function useRemoveLogo() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => del<undefined>("/workshop/logo"),
    onSuccess: () => void client.invalidateQueries({ queryKey: workshopKeys.workshop }),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) => post<undefined>("/me/password", body),
  });
}

export function useTotpSetup() {
  return useMutation({ mutationFn: () => post<TotpSetup>("/me/totp/setup") });
}

export function useTotpEnable() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { secret: string; code: string }) => post<Me>("/me/totp/enable", body),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

export function useTotpDisable() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => post<Me>("/me/totp/disable"),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}
