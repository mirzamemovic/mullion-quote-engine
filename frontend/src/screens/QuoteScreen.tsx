/**
 * One quote: its windows, the price the client sees, and what each number is made of.
 * The total is the largest number on the screen; any line opens into its layers.
 */
import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import {
  useAddPayment,
  useCalculation,
  useNewRevision,
  usePayments,
  useQuote,
  useSaveRevision,
  useSetStatus,
} from "../api/queries";
import type { Calculation, PositionOut, PositionPrice, QuoteDetail, QuoteStatus } from "../api/types";
import { Icon } from "../components/Icon";
import { Button, ErrorNote, Field, Loading, SizeMark, TopBar } from "../components/ui";
import { WindowDrawing } from "../components/WindowDrawing";
import { day, euros, isoDate, size } from "../lib/format";
import { workshopLabel } from "../lib/labels";
import { revisionBody } from "../lib/revision";
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

        {draft && positions.length > 0 && <Adjustments quote={quote} />}

        {calc.data && Object.keys(calc.data.plans).length > 0 && (
          <CuttingPlan calculation={calc.data} />
        )}

        {(status === "accepted" || quote.paid_cents > 0) && <Payments quote={quote} />}
      </main>

      {positions.length > 0 && <TotalSheet quote={quote} calculation={calc.data} />}
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
              {price ? euros(price.total_cents, lang) : "–"}
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
              <Row label={t("summary.unitPrice", { qty: p.qty, unit: euros(price.unit_price_cents, lang) })} value={euros(price.total_cents, lang)} strong />
              {price.material.map((line, i) => (
                <Row key={i} label={workshopLabel(line.label, lang)} value={euros(line.cents, lang)} soft />
              ))}
              <Row label={t("summary.material")} value={euros(price.material_cents, lang)} />
              <Row label={t("summary.margin")} value={euros(price.margin_cents, lang)} />
              <Row label={t("summary.labour")} value={euros(price.labour_cents, lang)} />
              {price.installation.map((line, i) => (
                <Row key={i} label={workshopLabel(line.label, lang)} value={euros(line.cents, lang)} soft />
              ))}
              {price.rounding_cents !== 0 && (
                <Row label={t("summary.rounding")} value={euros(price.rounding_cents, lang)} soft />
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
  const [discount, setDiscount] = useState(rev.discount_cents ? String(rev.discount_cents / 100) : "");
  const [km, setKm] = useState(rev.transport_km ? String(rev.transport_km) : "");
  const [openForm, setOpenForm] = useState(false);
  const cents = Math.round(Number(discount.replace(",", ".") || "0") * 100);
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
              body: { ...revisionBody(quote), discount_cents: Number.isFinite(cents) ? Math.max(0, cents) : 0, discount_bp: 0, transport_km: Number(km || 0) },
            });
          }}
        >
          <Field label={t("summary.discountEuro")} inputMode="decimal" value={discount} onChange={(e) => setDiscount(e.target.value.replace(/[^\d,.]/g, ""))} />
          <Field label={t("summary.transportKm")} inputMode="numeric" value={km} onChange={(e) => setKm(e.target.value.replace(/\D/g, "").slice(0, 4))} />
          <Button type="submit" tone="secondary" className="col-span-2" busy={save.isPending}>
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
  const cents = Math.round(Number(amount.replace(",", ".") || "0") * 100);
  const kind = quote.paid_cents > 0 ? "balance" : "advance";
  return (
    <section className="mx-4 mt-6 rounded-slot bg-board p-4" aria-labelledby="payments">
      <h2 id="payments" className="text-lg font-extrabold">
        {t("summary.payments")}
      </h2>
      {quote.total_cents != null && (
        <p className="mt-1 text-base text-graphite-soft">
          {t("summary.paidTotal", { paid: euros(quote.paid_cents, lang), total: euros(quote.total_cents, lang) })}
        </p>
      )}
      <ul className="mt-2 space-y-1">
        {(payments.data ?? []).map((p) => (
          <li key={p.id} className="flex justify-between text-base">
            <span>
              {t(`summary.${p.kind}`)} · {day(p.received_on, lang)}
            </span>
            <span className="figure text-figure-sm">{euros(p.amount_cents, lang)}</span>
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
          <Field label={`${t(`summary.${kind}`)} · ${t("summary.amount")}`} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d,.]/g, ""))} />
          <Field label={t("summary.receivedOn")} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <Button type="submit" tone="secondary" className="col-span-2" icon="plus" busy={add.isPending} disabled={cents <= 0}>
            {t("summary.addPayment")}
          </Button>
        </form>
      )}
    </section>
  );
}

function shareText(quote: QuoteDetail, calc: Calculation, t: TFunction, lang: string): string {
  const lines = [`${t("quotes.title")} ${quote.number} · ${quote.client_name}`];
  const prices = new Map(calc.price.positions.map((p) => [p.ref, p]));
  for (const p of quote.revision.positions) {
    const price = prices.get(p.ref);
    lines.push(`${p.ref} ${t(`types.${p.construction_type}`)} ${size(p.width_mm, p.height_mm)} mm × ${p.qty}: ${price ? euros(price.total_cents, lang) : ""}`);
  }
  lines.push(`${t("summary.total")}: ${euros(calc.price.total_cents, lang)}`);
  if (quote.valid_until) lines.push(t("summary.validUntil", { date: day(quote.valid_until, lang) }));
  return lines.join("\n");
}

function TotalSheet({ quote, calculation }: { quote: QuoteDetail; calculation: Calculation | undefined }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const navigate = useNavigate();
  const [explain, setExplain] = useState(false);
  const setStatus = useSetStatus(quote.id);
  const newRevision = useNewRevision(quote.id);
  const status = quote.status as QuoteStatus;
  const price = calculation?.price;

  async function share() {
    if (!calculation) return;
    const text = shareText(quote, calculation, t, lang);
    if (typeof navigator.share === "function") {
      await navigator.share({ title: quote.number, text }).catch(() => undefined);
    } else {
      await navigator.clipboard?.writeText(text);
    }
    if (status === "draft") setStatus.mutate("sent");
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
          {price ? euros(price.total_cents, lang) : "–"}
        </p>
        {explain && price && (
          <dl className="mt-2 max-h-[45dvh] space-y-1 overflow-y-auto rounded-slot bg-plaster p-3 text-base">
            {price.positions.map((p) => (
              <Row key={p.ref} label={p.ref} value={euros(p.total_cents, lang)} soft />
            ))}
            {price.extras.map((line, i) => (
              <Row key={`e${i}`} label={workshopLabel(line.label, lang)} value={euros(line.cents, lang)} soft />
            ))}
            {price.transport_cents > 0 && <Row label={t("summary.transport")} value={euros(price.transport_cents, lang)} soft />}
            {price.discount_cents > 0 && (
              <>
                <Row label={t("summary.subtotal")} value={euros(price.subtotal_cents, lang)} />
                <Row label={t("summary.discount")} value={euros(-price.discount_cents, lang)} />
              </>
            )}
            {(price.discount_cents > 0 || price.vat_cents > 0) && (
              <Row label={t("summary.net")} value={euros(price.net_cents, lang)} />
            )}
            {price.vat_cents > 0 && <Row label={t("summary.vat")} value={euros(price.vat_cents, lang)} />}
            <Row label={t("summary.total")} value={euros(price.total_cents, lang)} strong />
            <Row label={t("summary.advance")} value={euros(price.advance_cents, lang)} soft />
            <Row label={t("summary.balance")} value={euros(price.balance_cents, lang)} soft />
          </dl>
        )}
        {setStatus.isError && (
          <p role="alert" className="mt-2 font-semibold text-crayon">
            {setStatus.error.message}
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
