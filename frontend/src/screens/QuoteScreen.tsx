/**
 * One quote: its windows, the price the client sees, and what each number is made of.
 * The total is the largest number on the screen; any line opens into its layers.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { type DocumentLanguage, useCalculation, useMe, useQuote } from "../api/queries";
import type { QuoteDetail, QuoteStatus } from "../api/types";
import { Icon } from "../components/Icon";
import { ErrorNote, Loading, TopBar } from "../components/ui";
import { WindowDrawing } from "../components/WindowDrawing";
import { day } from "../lib/format";
import { CuttingPlan } from "./CuttingPlan";
import { StatusPill } from "./StatusPill";
import { PositionRow } from "./quote/PositionRow";
import { Adjustments } from "./quote/Adjustments";
import { Payments } from "./quote/Payments";
import { TotalSheet } from "./quote/TotalSheet";
import { Documents } from "./quote/Documents";
import { Extras } from "./quote/Extras";

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
