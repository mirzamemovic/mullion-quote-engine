/**
 * The cutting plan, per stock bar. Each bar is drawn as a strip and listed like a timed tape
 * side: the pieces with their lengths flush right, the offcut as the last line.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Calculation, Piece } from "../api/types";
import { Icon } from "../components/Icon";
import { cutLabel, workshopLabel } from "../lib/labels";

function pieceIndex(calculation: Calculation): Map<string, Piece> {
  const index = new Map<string, Piece>();
  for (const list of Object.values(calculation.cut_lists)) {
    for (const piece of [...list.pieces, ...list.steel]) {
      index.set(`${piece.position_ref} ${piece.label}`, piece);
    }
  }
  return index;
}

export function CuttingPlan({ calculation }: { calculation: Calculation }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const [open, setOpen] = useState(false);
  const pieces = pieceIndex(calculation);
  const groups = Object.entries(calculation.plans);
  const bars = groups.reduce((sum, [, plan]) => sum + plan.plan.bars.length, 0);
  return (
    <section className="mx-4 mt-6" aria-labelledby="cutting-plan">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex min-h-14 w-full items-center justify-between rounded-slot bg-board px-4 text-left"
      >
        <span id="cutting-plan" className="text-lg font-extrabold">
          {t("summary.cuttingPlan")}
        </span>
        <span className="flex items-center gap-2 text-base font-semibold text-graphite-soft">
          {t("summary.bars", { count: bars })}
          <Icon name={open ? "minus" : "plus"} className="size-5" />
        </span>
      </button>
      {open && (
        <div className="mt-2 space-y-5">
          {groups.map(([name, plan]) => (
            <div key={name}>
              <h3 className="flex items-baseline justify-between px-1 text-base font-extrabold">
                <span>{workshopLabel(name, lang)}</span>
                <span className="figure text-figure-sm text-graphite-soft">
                  {plan.plan.bars.length} × {plan.plan.bar_length_mm}
                </span>
              </h3>
              <ol className="mt-2 space-y-3">
                {plan.plan.bars.map((bar, b) => (
                  <li key={b} className="rounded-slot bg-board p-3">
                    <div className="flex h-5 overflow-hidden rounded-sm border-2 border-graphite" aria-hidden="true">
                      {bar.cuts.map((key, c) => {
                        const length = pieces.get(key)?.length_mm ?? 0;
                        return (
                          <span
                            key={c}
                            className="border-r-2 border-graphite bg-chalk-tint last:border-r-0"
                            style={{ width: `${(length / plan.plan.bar_length_mm) * 100}%` }}
                          />
                        );
                      })}
                      <span className="flex-1 bg-[repeating-linear-gradient(135deg,var(--color-plaster-deep)_0_4px,transparent_4px_8px)]" />
                    </div>
                    <dl className="mt-2 space-y-0.5 text-base">
                      {bar.cuts.map((key, c) => {
                        const piece = pieces.get(key);
                        return (
                          <div key={c} className="flex items-baseline justify-between gap-3">
                            <dt className="min-w-0 truncate">{cutLabel(key, piece?.position_ref, lang)}</dt>
                            <dd className="figure shrink-0 text-figure-sm">{piece?.length_mm ?? "?"}</dd>
                          </div>
                        );
                      })}
                      <div className="flex items-baseline justify-between gap-3 border-t-2 border-plaster pt-1 text-graphite-soft">
                        <dt>{t("summary.offcut")}</dt>
                        <dd className="figure text-figure-sm">{bar.offcut_mm}</dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
