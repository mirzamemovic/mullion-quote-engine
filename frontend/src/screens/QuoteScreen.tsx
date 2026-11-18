/**
 * One quote: its windows, the price the client sees, and what each number is made of.
 * The total is the largest number on the screen; any line opens into its layers.
 */
import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import {
  type DocumentKind,
  type DocumentLanguage,
  useAddPayment,
  useCalculation,
  useDocument,
  useMe,
  useNewRevision,
  usePayments,
  useQuote,
  useSaveRevision,
  useSetStatus,
} from "../api/queries";
import type { Calculation, ExtraIn, PositionOut, PositionPrice, QuoteDetail, QuoteStatus } from "../api/types";
import { usePriceList } from "../api/workshop";
import { Icon } from "../components/Icon";
import { Button, ErrorNote, Field, IconButton, Loading, Note, Segmented, Select, SizeMark, TopBar } from "../components/ui";
import { WindowDrawing } from "../components/WindowDrawing";
import { currencySymbol, day, isoDate, money, moneyInput, parseMoney, size } from "../lib/format";
import { unitLabel, workshopLabel } from "../lib/labels";
import { revisionBody } from "../lib/revision";
import { saveFile, type ShareResult, shareFile, shareText } from "../lib/share";
import { CuttingPlan } from "./CuttingPlan";
import { StatusPill } from "./StatusPill";

export function QuoteScreen() {
  const { id = "" } = useParams();
  const quote = useQuote(id);
  if (quote.isPending) return <Loading />;
  if (quote.isError) {
    return <ErrorNote message={quote.error.message} onRetry={() => void quote.refetch()} />;
  }
  return <Quote quote={quote.data} />;
}

function Quote({ quote }: { quote: QuoteDetail }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const status = quote.status as QuoteStatus;
  const positions = quote.revision.positions;
  const calc = useCalculation(quote.id, quote.revision_no, positions.length > 0);
  const [open, setOpen] = useState<string | null>(null);
  const me = useMe();
  // The client's PDF is in the workshop's language unless he picks the other one.
  const [pdfLang, setPdfLang] = useState<DocumentLanguage>(() => (me.data?.language === "bs" ? "bs" : "en"));
  const draft = status === "draft";
  const prices = new Map((calc.data?.price.positions ?? []).map((p) => [p.ref, p]));

  return (
    <>
      <TopBar
        title={quote.client_name}
        subtitle={`${quote.number} · ${t("summary.revision", { n: quote.revision_no })}`}
        back="/"
        actions={<StatusPill status={status} />}
      />
      <main className="mx-auto max-w-3xl pb-72">
        <section className="px-4 pt-5" aria-labelledby="positions">
          <div className="flex items-end justify-between gap-3">
            <h2 id="positions" className="text-2xl font-extrabold">
              {t("summary.positions")}
            </h2>
            {quote.valid_until && (
              <p className="text-sm font-semibold text-graphite-soft">
                {t("summary.validUntil", { date: day(quote.valid_until, lang) })}
              </p>
            )}
          </div>

          {positions.length === 0 && (
            <div className="mt-4 rounded-slot bg-board p-6 text-center">
              <WindowDrawing type="single_sash_tilt_turn" width={1200} height={1400} openings={["tilt_turn_left"]} className="mx-auto h-28 w-28 opacity-60" />
              <p className="mt-3 text-lg font-semibold">{t("summary.empty")}</p>
            </div>
          )}

          <ul className="mt-3 space-y-2">
            {positions.map((p) => (
              <PositionRow
                key={p.ref}
                quote={quote}
                position={p}
                price={prices.get(p.ref)}
                editable={draft}
                open={open === p.ref}
                onToggle={() => setOpen(open === p.ref ? null : p.ref)}
              />
            ))}
          </ul>

          {draft && (
            <div className="mt-3">
              <Link
                to={`/quotes/${quote.id}/positions/new`}
                className="flex min-h-14 items-center justify-center gap-2 rounded-slot bg-chalk px-5 text-lg font-bold text-white hover:bg-chalk-deep"
              >
                <Icon name="plus" />
                {t("summary.addPosition")}
              </Link>
              {positions.length > 0 && (
                <Link
                  to={`/quotes/${quote.id}/positions/new?copy=${encodeURIComponent(positions[positions.length - 1]?.ref ?? "")}`}
                  className="mt-1 flex min-h-12 items-center justify-center gap-2 text-base font-bold text-chalk underline decoration-2 underline-offset-4"
                >
                  <Icon name="copy" className="size-5" />
                  {t("summary.copyPosition")}
                </Link>
              )}
            </div>
          )}
        </section>

        {calc.isError && (
          <ErrorNote message={t("summary.missing", { detail: calc.error.message })} onRetry={() => void calc.refetch()} />
        )}

        {calc.data && calc.data.warnings.length > 0 && (
          <section className="mx-4 mt-6 rounded-slot bg-crayon-tint p-4" aria-labelledby="warnings">
            <h2 id="warnings" className="flex items-center gap-2 text-lg font-extrabold text-crayon">
              <Icon name="alert" className="size-5" />
              {t("summary.warnings")}
            </h2>
            <ul className="mt-2 space-y-1.5">
              {calc.data.warnings.map((w, i) => (
                <li key={i} className="text-base">
                  {w.position_ref && <strong className="mr-1">{w.position_ref}:</strong>}
                  {w.message}
                </li>
              ))}
            </ul>
          </section>
        )}

        {(draft || quote.revision.extra_lines.length > 0) && <Extras quote={quote} lines={calc.data?.price.extras} editable={draft} />}
        {draft && positions.length > 0 && <Adjustments quote={quote} />}

        {calc.data && Object.keys(calc.data.plans).length > 0 && (
          <CuttingPlan calculation={calc.data} />
        )}

        {calc.data && <Documents quote={quote} language={pdfLang} onLanguage={setPdfLang} />}

        {(status === "accepted" || quote.paid_cents > 0) && <Payments quote={quote} />}
      </main>

      {positions.length > 0 && <TotalSheet quote={quote} calculation={calc.data} pdfLang={pdfLang} />}
    </>
  );
}

function PositionRow({
  quote,
  position: p,
  price,
  editable,
  open,
  onToggle,
}: {
  quote: QuoteDetail;
  position: PositionOut;
  price: PositionPrice | undefined;
  editable: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const save = useSaveRevision(quote.id);
  return (
    <li className={`rounded-slot bg-board ${open ? "shadow-lift" : ""}`}>
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className="flex w-full items-center gap-3 p-3 text-left"
      >
        <WindowDrawing
          type={p.construction_type}
          width={p.width_mm}
          height={p.height_mm}
          openings={p.openings}
          colour={p.colour}
          className="size-16 shrink-0"
          stroke={1.25}
        />
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate text-lg font-bold">{p.ref}</span>
            <span className="figure shrink-0 text-figure-md">
              {price ? money(price.total_cents, lang) : "–"}
            </span>
          </span>
          <span className="block truncate text-base text-graphite-soft">
            {t(`types.${p.construction_type}`)}
          </span>
          <span className="flex items-end gap-1.5 text-figure-sm">
            <SizeMark>{size(p.width_mm, p.height_mm)}</SizeMark>
            <span className="figure mb-2 text-graphite-soft">
              mm{p.qty > 1 ? ` · ${t("position.pieces", { count: p.qty })}` : ""}
            </span>
          </span>
        </span>
      </button>
      {open && (
        <div className="border-t-2 border-plaster px-3 pt-3 pb-3">
          {price && (
            <dl className="space-y-1 text-base">
              <Row label={t("summary.unitPrice", { qty: p.qty, unit: money(price.unit_price_cents, lang) })} value={money(price.total_cents, lang)} strong />
              <p className="text-sm text-graphite-soft">{t("summary.perM2", { amount: money(price.cents_per_m2, lang) })}</p>
              {price.material.map((line, i) => (
                <Row key={i} label={workshopLabel(line.label, lang)} value={money(line.cents, lang)} soft />
              ))}
              <Row label={t("summary.material")} value={money(price.material_cents, lang)} />
              <Row label={t("summary.margin")} value={money(price.margin_cents, lang)} />
              <Row label={t("summary.labour")} value={money(price.labour_cents, lang)} />
              {price.installation.map((line, i) => (
                <Row key={i} label={workshopLabel(line.label, lang)} value={money(line.cents, lang)} soft />
              ))}
              {price.rounding_cents !== 0 && (
                <Row label={t("summary.rounding")} value={money(price.rounding_cents, lang)} soft />
              )}
            </dl>
          )}
          {editable && (
            <div className="mt-3 flex gap-2">
              <Link
                to={`/quotes/${quote.id}/positions/${encodeURIComponent(p.ref)}`}
                className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-slot border-2 border-graphite font-bold hover:bg-plaster"
              >
                <Icon name="edit" className="size-5" />
                {t("summary.edit")}
              </Link>
              <button
                type="button"
                disabled={save.isPending}
                onClick={() => save.mutate({ revision: quote.revision_no, body: revisionBody(quote, { remove: p.ref }) })}
                className="flex min-h-12 items-center justify-center gap-2 rounded-slot border-2 border-graphite-line px-4 font-bold text-graphite hover:bg-plaster"
              >
                <Icon name="trash" className="size-5" />
                {t("summary.remove")}
              </button>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function Row({ label, value, strong, soft }: { label: string; value: string; strong?: boolean; soft?: boolean }) {
  return (
    <div className={`flex items-baseline justify-between gap-4 ${soft ? "pl-3 text-graphite-soft" : ""} ${strong ? "font-bold" : ""}`}>
      <dt className="min-w-0">{label}</dt>
      <dd className="figure shrink-0 text-figure-sm">{value}</dd>
    </div>
  );
}

function Adjustments({ quote }: { quote: QuoteDetail }) {
  const { t } = useTranslation();
  const save = useSaveRevision(quote.id);
  const rev = quote.revision;
  const { i18n } = useTranslation();
  const [discount, setDiscount] = useState(rev.discount_cents ? moneyInput(rev.discount_cents, i18n.language) : "");
  const [km, setKm] = useState(rev.transport_km ? String(rev.transport_km) : "");
  const [openForm, setOpenForm] = useState(false);
  const cents = discount.trim() ? parseMoney(discount) : 0;
  return (
    <section className="mx-4 mt-6">
      <button
        type="button"
        aria-expanded={openForm}
        onClick={() => setOpenForm(!openForm)}
        className="flex min-h-12 items-center gap-2 text-base font-bold text-chalk underline decoration-2 underline-offset-4"
      >
        <Icon name="sliders" className="size-5" />
        {t("summary.settings")}
      </button>
      {openForm && (
        <form
          className="mt-2 grid grid-cols-2 gap-3 rounded-slot bg-board p-3"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate({
              revision: quote.revision_no,
              body: { ...revisionBody(quote), discount_cents: cents ?? 0, discount_bp: 0, transport_km: Number(km || 0) },
            });
          }}
        >
          <Field label={t("summary.discountEuro", { currency: currencySymbol() })} error={cents === null ? t("errors.number") : undefined} inputMode="decimal" value={discount} onChange={(e) => setDiscount(e.target.value.replace(/[^\d,.]/g, ""))} />
          <Field label={t("summary.transportKm")} inputMode="numeric" value={km} onChange={(e) => setKm(e.target.value.replace(/\D/g, "").slice(0, 4))} />
          <Button type="submit" tone="secondary" className="col-span-2" busy={save.isPending} disabled={cents === null}>
            {t("app.save")}
          </Button>
        </form>
      )}
    </section>
  );
}

function Payments({ quote }: { quote: QuoteDetail }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const payments = usePayments(quote.id, true);
  const add = useAddPayment(quote.id);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(isoDate(new Date()));
  const cents = parseMoney(amount) ?? 0;
  const kind = quote.paid_cents > 0 ? "balance" : "advance";
  return (
    <section className="mx-4 mt-6 rounded-slot bg-board p-4" aria-labelledby="payments">
      <h2 id="payments" className="text-lg font-extrabold">
        {t("summary.payments")}
      </h2>
      {quote.total_cents != null && (
        <p className="mt-1 text-base text-graphite-soft">
          {t("summary.paidTotal", { paid: money(quote.paid_cents, lang), total: money(quote.total_cents, lang) })}
        </p>
      )}
      <ul className="mt-2 space-y-1">
        {(payments.data ?? []).map((p) => (
          <li key={p.id} className="flex justify-between text-base">
            <span>
              {t(`summary.${p.kind}`)} · {day(p.received_on, lang)}
            </span>
            <span className="figure text-figure-sm">{money(p.amount_cents, lang)}</span>
          </li>
        ))}
      </ul>
      {quote.status === "accepted" && (
        <form
          className="mt-3 grid grid-cols-2 gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (cents > 0) add.mutate({ kind, amount_cents: cents, received_on: date }, { onSuccess: () => setAmount("") });
          }}
        >
          <Field label={`${t(`summary.${kind}`)} · ${t("summary.amount", { currency: currencySymbol() })}`} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d,.]/g, ""))} />
          <Field label={t("summary.receivedOn")} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <Button type="submit" tone="secondary" className="col-span-2" icon="plus" busy={add.isPending} disabled={cents <= 0}>
            {t("summary.addPayment")}
          </Button>
        </form>
      )}
    </section>
  );
}

function summaryText(quote: QuoteDetail, calc: Calculation, t: TFunction, lang: string): string {
  const lines = [`${t("quotes.title")} ${quote.number} · ${quote.client_name}`];
  const prices = new Map(calc.price.positions.map((p) => [p.ref, p]));
  for (const p of quote.revision.positions) {
    const price = prices.get(p.ref);
    lines.push(`${p.ref} ${t(`types.${p.construction_type}`)} ${size(p.width_mm, p.height_mm)} mm × ${p.qty}: ${price ? money(price.total_cents, lang) : ""}`);
  }
  lines.push(`${t("summary.total")}: ${money(calc.price.total_cents, lang)}`);
  if (quote.valid_until) lines.push(t("summary.validUntil", { date: day(quote.valid_until, lang) }));
  return lines.join("\n");
}

/** The client quote and the workshop sheet as PDFs, and the language of the client's copy. */
function Documents({
  quote,
  language,
  onLanguage,
}: {
  quote: QuoteDetail;
  language: DocumentLanguage;
  onLanguage: (lang: DocumentLanguage) => void;
}) {
  const { t } = useTranslation();
  const pdf = useDocument(quote.id, quote.revision_no);
  const [kind, setKind] = useState<DocumentKind>("quote");
  const download = (next: DocumentKind) => {
    setKind(next);
    pdf.mutate({ kind: next, lang: language }, { onSuccess: saveFile });
  };
  return (
    <section className="mx-4 mt-6 space-y-3" aria-labelledby="documents">
      <h2 id="documents" className="text-xl font-extrabold">
        {t("documents.title")}
      </h2>
      <Segmented
        label={t("documents.language")}
        value={language}
        onChange={onLanguage}
        options={[
          { value: "en", label: t("profile.en") },
          { value: "bs", label: t("profile.bs") },
        ]}
      />
      <div className="grid gap-2 sm:grid-cols-2">
        <Button tone="secondary" icon="download" busy={pdf.isPending && kind === "quote"} disabled={pdf.isPending} onClick={() => download("quote")}>
          {t("documents.quote")}
        </Button>
        <Button tone="secondary" icon="download" busy={pdf.isPending && kind === "workshop"} disabled={pdf.isPending} onClick={() => download("workshop")}>
          {t("documents.workshop")}
        </Button>
      </div>
      {pdf.isError && <Note>{pdf.error.message}</Note>}
    </section>
  );
}

function TotalSheet({
  quote,
  calculation,
  pdfLang,
}: {
  quote: QuoteDetail;
  calculation: Calculation | undefined;
  pdfLang: DocumentLanguage;
}) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const navigate = useNavigate();
  const [explain, setExplain] = useState(false);
  const setStatus = useSetStatus(quote.id);
  const newRevision = useNewRevision(quote.id);
  const pdf = useDocument(quote.id, quote.revision_no);
  // A PDF made but not yet handed on, when the browser asked for a fresh tap first.
  // Kept with what it was made from, so a changed language or price makes a new one.
  const [ready, setReady] = useState<{ file: File; made: string } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const status = quote.status as QuoteStatus;
  const price = calculation?.price;

  /** The client PDF through the share sheet (download where files cannot be shared). If no PDF
   * can be made, the summary goes as text instead. A draft becomes "sent" once it went out. */
  async function share() {
    if (!calculation) return;
    setNote(null);
    const text = summaryText(quote, calculation, t, lang);
    let result: ShareResult;
    const made = `${pdfLang}:${calculation.price.total_cents}`;
    let file = ready?.made === made ? ready.file : null;
    if (!file) {
      try {
        file = await pdf.mutateAsync({ kind: "quote", lang: pdfLang });
      } catch (error) {
        setNote(t("documents.textInstead", { reason: error instanceof Error ? error.message : "" }));
        file = null;
      }
    }
    if (file) {
      result = await shareFile(file, text);
      if (result === "blocked") {
        setReady({ file, made });
        setNote(t("documents.tapAgain"));
        return;
      }
      setReady(null);
    } else {
      result = await shareText(quote.number, text);
    }
    if (result !== "cancelled" && status === "draft") setStatus.mutate("sent");
  }

  return (
    <section
      aria-labelledby="total"
      className="fixed inset-x-0 bottom-0 z-20 border-t-2 border-plaster-deep bg-board shadow-sheet"
    >
      <div className="mx-auto max-w-3xl px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <div className="flex items-center justify-between gap-3">
          <p id="total" className="text-base font-semibold text-graphite-soft">
            {t("summary.total")}
          </p>
          {price && (
            <button
              type="button"
              aria-expanded={explain}
              onClick={() => setExplain(!explain)}
              className="min-h-11 text-base font-bold text-chalk underline decoration-2 underline-offset-4"
            >
              {explain ? t("summary.hide") : t("summary.explain")}
            </button>
          )}
        </div>
        <p className="figure text-figure-lg whitespace-nowrap" aria-live="polite">
          {price ? money(price.total_cents, lang) : "–"}
        </p>
        {explain && price && (
          <dl className="mt-2 max-h-[45dvh] space-y-1 overflow-y-auto rounded-slot bg-plaster p-3 text-base">
            {price.positions.map((p) => (
              <Row key={p.ref} label={p.ref} value={money(p.total_cents, lang)} soft />
            ))}
            {price.extras.map((line, i) => (
              <Row key={`e${i}`} label={workshopLabel(line.label, lang)} value={money(line.cents, lang)} soft />
            ))}
            {price.transport_cents > 0 && <Row label={t("summary.transport")} value={money(price.transport_cents, lang)} soft />}
            {price.discount_cents > 0 && (
              <>
                <Row label={t("summary.subtotal")} value={money(price.subtotal_cents, lang)} />
                <Row label={t("summary.discount")} value={money(-price.discount_cents, lang)} />
              </>
            )}
            {(price.discount_cents > 0 || price.vat_cents > 0) && (
              <Row label={t("summary.net")} value={money(price.net_cents, lang)} />
            )}
            {price.vat_cents > 0 && <Row label={t("summary.vat")} value={money(price.vat_cents, lang)} />}
            <Row label={t("summary.total")} value={money(price.total_cents, lang)} strong />
            <Row label={t("summary.advance")} value={money(price.advance_cents, lang)} soft />
            <Row label={t("summary.balance")} value={money(price.balance_cents, lang)} soft />
          </dl>
        )}
        {setStatus.isError && (
          <p role="alert" className="mt-2 font-semibold text-crayon">
            {setStatus.error.message}
          </p>
        )}
        {note && (
          <p role="status" className="mt-2 text-base font-semibold text-graphite-soft">
            {note}
          </p>
        )}
        <div className="mt-3 grid grid-cols-2 gap-2">
          {status === "draft" && (
            <Button className="col-span-2" icon="share" disabled={!calculation} onClick={() => void share()}>
              {t("summary.share")}
            </Button>
          )}
          {(status === "sent" || status === "expired") && (
            <>
              <Button icon="check" busy={setStatus.isPending} onClick={() => setStatus.mutate("accepted")} disabled={status === "expired"}>
                {t("summary.accept")}
              </Button>
              <Button tone="danger" busy={setStatus.isPending} onClick={() => setStatus.mutate("rejected")}>
                {t("summary.reject")}
              </Button>
              <Button tone="secondary" className="col-span-2" icon="share" onClick={() => void share()}>
                {t("summary.share")}
              </Button>
            </>
          )}
          {(status === "sent" || status === "rejected" || status === "expired") && (
            <Button
              tone="quiet"
              className="col-span-2"
              busy={newRevision.isPending}
              onClick={() => newRevision.mutate(undefined, { onSuccess: () => void navigate(`/quotes/${quote.id}`) })}
            >
              {t("summary.newRevision")}
            </Button>
          )}
          {status === "accepted" && (
            <p className="col-span-2 flex items-center gap-2 text-base font-semibold text-tick">
              <Icon name="check" className="size-5" />
              {t("summary.lockedNote")}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

const EXTRA_KINDS = ["sill", "shutter", "screen", "other"] as const;
type ExtraKind = (typeof EXTRA_KINDS)[number];

/**
 * Sills (per metre), roller shutters and insect screens (per m²) from the quote's price list,
 * and manual lines with their own price. The engine prices them; this only collects them.
 */
function Extras({ quote, lines, editable }: { quote: QuoteDetail; lines: { label: string; cents: number }[] | undefined; editable: boolean }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const save = useSaveRevision(quote.id);
  const prices = usePriceList(quote.revision.price_list_version_id);
  const [adding, setAdding] = useState(false);
  const [kind, setKind] = useState<ExtraKind>("sill");
  const [ref, setRef] = useState("");
  const [qty, setQty] = useState("1");
  const [length, setLength] = useState("");
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const extras = quote.revision.extra_lines;
  const products = (prices.data?.entries ?? []).filter((e) => e.item_kind === kind);
  const product = products.find((e) => e.item_ref === ref) ?? products[0];
  const n = Number(qty);
  const manual = parseMoney(price);
  let extra: ExtraIn | null = null;
  if (kind === "other") {
    if (description.trim() && manual !== null && n >= 1) {
      extra = { kind, ref: description.trim().slice(0, 50), qty: n, manual_price_cents: manual, description: description.trim() };
    }
  } else if (product && n >= 1) {
    if (kind === "sill" && Number(length) > 0) {
      extra = { kind, ref: product.item_ref, qty: n, colour: product.colour ?? "white", length_mm: Number(length), description: "" };
    } else if (kind !== "sill" && Number(width) > 0 && Number(height) > 0) {
      extra = { kind, ref: product.item_ref, qty: n, area_mm2: Number(width) * Number(height), description: "" };
    }
  }
  const store = (next: ExtraIn[]) =>
    save.mutate({ revision: quote.revision_no, body: { ...revisionBody(quote), extras: next } }, { onSuccess: () => setAdding(false) });
  const digits = (set: (v: string) => void, count: number) => (e: { target: { value: string } }) =>
    set(e.target.value.replace(/\D/g, "").slice(0, count));

  return (
    <section className="mx-4 mt-6 space-y-3" aria-labelledby="extras">
      <h2 id="extras" className="text-xl font-extrabold">
        {t("extras.title")}
      </h2>
      {extras.length > 0 && (
        <ul className="space-y-2">
          {extras.map((e, i) => (
            <li key={`${e.kind}-${e.ref}-${i}`} className="flex items-center gap-3 rounded-slot bg-board px-4 py-3">
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">
                  {t(`extras.${e.kind}`)} · {e.kind === "other" ? e.description || e.ref : e.ref}
                </span>
                <span className="block text-sm text-graphite-soft">
                  {e.qty} × {e.length_mm ? `${e.length_mm} mm` : e.area_mm2 ? `${(e.area_mm2 / 1_000_000).toFixed(2)} m²` : ""}
                </span>
              </span>
              {lines?.[i] && <span className="figure shrink-0 text-figure-sm">{money(lines[i].cents, lang)}</span>}
              {editable && (
                <IconButton
                  icon="trash"
                  label={t("app.remove")}
                  className="text-graphite-soft hover:bg-plaster"
                  onClick={() => store((revisionBody(quote).extras ?? []).filter((_, j) => j !== i))}
                />
              )}
            </li>
          ))}
        </ul>
      )}
      {editable && !adding && (
        <Button tone="secondary" icon="plus" className="w-full" onClick={() => setAdding(true)}>
          {t("extras.add")}
        </Button>
      )}
      {editable && adding && (
        <form
          className="grid grid-cols-2 gap-3 rounded-slot bg-board p-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (extra) store([...(revisionBody(quote).extras ?? []), extra]);
          }}
        >
          <div className="col-span-2">
            <Segmented
              wrap
              label={t("extras.kind")}
              value={kind}
              onChange={(k) => {
                setKind(k);
                setRef("");
              }}
              options={EXTRA_KINDS.map((k) => ({ value: k, label: t(`extras.${k}`) }))}
            />
          </div>
          {kind === "other" ? (
            <>
              <Field className="col-span-2" label={t("extras.description")} value={description} onChange={(e) => setDescription(e.target.value.slice(0, 200))} />
              <Field label={t("extras.price", { currency: currencySymbol() })} inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^\d,.]/g, ""))} />
            </>
          ) : products.length === 0 ? (
            <p className="col-span-2 text-graphite-soft">{t("extras.noProducts")}</p>
          ) : (
            <>
              <Select
                className="col-span-2"
                label={t("extras.ref")}
                value={product?.item_ref ?? ""}
                onChange={setRef}
                options={products.map((e) => ({ value: e.item_ref, label: `${e.item_ref} · ${money(e.amount_cents, lang)} / ${unitLabel(e.unit, lang)}` }))}
              />
              {kind === "sill" ? (
                <Field label={t("extras.length")} inputMode="numeric" value={length} onChange={digits(setLength, 5)} />
              ) : (
                <>
                  <Field label={t("extras.width")} inputMode="numeric" value={width} onChange={digits(setWidth, 4)} />
                  <Field label={t("extras.height")} inputMode="numeric" value={height} onChange={digits(setHeight, 4)} />
                </>
              )}
            </>
          )}
          <Field label={t("position.qty")} inputMode="numeric" value={qty} onChange={digits(setQty, 2)} />
          {save.isError && (
            <div className="col-span-2">
              <ErrorNote message={save.error.message} />
            </div>
          )}
          <Button type="submit" className="col-span-2" busy={save.isPending} disabled={!extra}>
            {t("extras.add")}
          </Button>
          <Button tone="quiet" className="col-span-2" onClick={() => setAdding(false)}>
            {t("app.cancel")}
          </Button>
        </form>
      )}
    </section>
  );
}
