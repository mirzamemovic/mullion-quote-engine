/** The bottom sheet: the total, its layers, and sending the quote to the client. */
import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { type DocumentLanguage, useDocument, useNewRevision, useSetStatus } from "../../api/queries";
import type { Calculation, QuoteDetail, QuoteStatus } from "../../api/types";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/ui";
import { day, money, size } from "../../lib/format";
import { workshopLabel } from "../../lib/labels";
import { type ShareResult, shareFile, shareText } from "../../lib/share";

import { Row } from "./Row";

export function summaryText(quote: QuoteDetail, calc: Calculation, t: TFunction, lang: string): string {
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
export function TotalSheet({
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
    const made = `${pdfLang}:${JSON.stringify(quote.revision)}`;
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
