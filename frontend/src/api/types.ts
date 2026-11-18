import type { Schemas } from "./client";

export type Me = Schemas["MeOut"];
export type QuoteSummary = Schemas["QuoteOut"];
export type QuoteDetail = Schemas["QuoteDetail"];
export type Client = Schemas["ClientOut"];
export type ClientIn = Schemas["ClientIn"];
export type ProfileSystem = Schemas["ProfileSystemOut"];
export type PositionIn = Schemas["PositionIn"];
export type PositionOut = Schemas["PositionOut"];
export type RevisionIn = Schemas["RevisionIn"];
export type ExtraIn = Schemas["ExtraIn"];
export type Measure = Schemas["MeasureOut"];
export type Payment = Schemas["PaymentOut"];
export type PriceList = Schemas["PriceListOut"];
export type Supplier = Schemas["SupplierOut"];
export type Settings = Schemas["SettingsIO"];
export type PriceEntry = Schemas["PriceEntryOut"];
export type PriceEntryIn = Schemas["PriceEntryIn"];
export type SetupStatus = Schemas["SetupStatusOut"];
export type SystemCheck = Schemas["SystemCheckOut"];
export type PriceCheck = Schemas["PriceCheckOut"];
export type Sheet = Schemas["SheetOut"];
export type SheetFields = Schemas["SheetFieldsOut"];
export type ProfileSystemIn = Schemas["ProfileSystemIn"];
export type HardwareSet = Schemas["HardwareSetOut"];
export type HardwareSetIn = Schemas["HardwareSetIn"];
export type ConstructionTypeState = Schemas["ConstructionTypeIO"];
export type User = Schemas["UserOut"];
export type SessionRow = Schemas["SessionOut"];
export type Invite = Schemas["InviteOut"];
export type InviteCreated = Schemas["InviteCreated"];
export type InviteInfo = Schemas["InviteInfo"];
export type Workshop = Schemas["WorkshopIO"];
export type TotpSetup = Schemas["TotpSetupOut"];
export type Role = "owner" | "staff";
export type Colour = PositionIn["colour"];
export type Opening = PositionIn["openings"][number];
export type QuoteStatus = "draft" | "sent" | "accepted" | "rejected" | "expired";

/* The calculation endpoint returns plain engine data (services/calculation.py). */

export interface Piece {
  position_ref: string;
  role: string;
  label: string;
  length_mm: number;
  angle_left: number;
  angle_right: number;
  qty: number;
  formula: string;
}

export interface GlassPane {
  position_ref: string;
  width_mm: number;
  height_mm: number;
  qty: number;
  build: string;
  formula_w: string;
  formula_h: string;
}

export interface CutList {
  pieces: Piece[];
  steel: Piece[];
  glass: GlassPane[];
  hardware_sets: { position_ref: string; opening: Opening; qty: number }[];
  gasket_mm: number;
}

export interface Bar {
  cuts: string[];
  used_mm: number;
  offcut_mm: number;
}

export interface Plan {
  plan: { bar_length_mm: number; bars: Bar[] };
  stats: {
    bars: number;
    waste_mm: number;
    waste_bp: number;
    kept_offcuts_mm: number[];
    scrap_mm: number;
    scrap_bp: number;
  };
}

export interface PriceLine {
  label: string;
  cents: number;
}

export interface PositionPrice {
  ref: string;
  material: PriceLine[];
  material_cents: number;
  margin_cents: number;
  labour_cents: number;
  installation: PriceLine[];
  installation_cents: number;
  rounding_cents: number;
  total_cents: number;
  unit_price_cents: number;
  area_mm2: number;
  cents_per_m2: number;
}

export interface JobPrice {
  positions: PositionPrice[];
  extras: PriceLine[];
  transport_cents: number;
  subtotal_cents: number;
  discount_cents: number;
  net_cents: number;
  vat_cents: number;
  total_cents: number;
  advance_cents: number;
  balance_cents: number;
}

export interface QuoteWarning {
  code: string;
  message: string;
  position_ref: string | null;
}

export interface Calculation {
  cut_lists: Record<string, CutList>;
  plans: Record<string, Plan>;
  price: JobPrice;
  warnings: QuoteWarning[];
  versions: { system_sheet: string; price_list: string };
}
