/** Sills, shutters, screens and manual lines of a quote. */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSaveRevision } from "../../api/queries";
import type { ExtraIn, QuoteDetail } from "../../api/types";
import { usePriceList } from "../../api/workshop";
import { Button, ErrorNote, Field, IconButton, Segmented, Select } from "../../components/ui";
import { currencySymbol, money, parseMoney } from "../../lib/format";
import { unitLabel } from "../../lib/labels";
import { revisionBody } from "../../lib/revision";

export const EXTRA_KINDS = ["sill", "shutter", "screen", "other"] as const;
export type ExtraKind = (typeof EXTRA_KINDS)[number];

/**
 * Sills (per metre), roller shutters and insect screens (per m²) from the quote's price list,
 * and manual lines with their own price. The engine prices them; this only collects them.
 */
export function Extras({ quote, lines, editable }: { quote: QuoteDetail; lines: { label: string; cents: number }[] | undefined; editable: boolean }) {
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
