/** One window of the quote: size, price, and its price layers when opened. */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useSaveRevision } from "../../api/queries";
import type { PositionOut, PositionPrice, QuoteDetail } from "../../api/types";
import { Icon } from "../../components/Icon";
import { SizeMark } from "../../components/ui";
import { WindowDrawing } from "../../components/WindowDrawing";
import { money, size } from "../../lib/format";
import { workshopLabel } from "../../lib/labels";
import { revisionBody } from "../../lib/revision";

import { Row } from "./Row";

export function PositionRow({
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
