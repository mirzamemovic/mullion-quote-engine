/** Discount, transport and margin of a draft quote. */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSaveRevision } from "../../api/queries";
import type { QuoteDetail } from "../../api/types";
import { Icon } from "../../components/Icon";
import { Button, Field } from "../../components/ui";
import { currencySymbol, moneyInput, parseMoney } from "../../lib/format";
import { revisionBody } from "../../lib/revision";

export function Adjustments({ quote }: { quote: QuoteDetail }) {
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
