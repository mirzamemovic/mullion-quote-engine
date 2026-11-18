/** Advance and balance payments of an accepted quote. */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAddPayment, usePayments } from "../../api/queries";
import type { QuoteDetail } from "../../api/types";
import { Button, Field } from "../../components/ui";
import { currencySymbol, day, isoDate, money, parseMoney } from "../../lib/format";

export function Payments({ quote }: { quote: QuoteDetail }) {
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
