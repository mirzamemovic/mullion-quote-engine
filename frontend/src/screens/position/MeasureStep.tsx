/**
 * Measuring, while measuring: the opening drawn from inside with each reading's slot where it is
 * taken. Typing jumps to the next slot as soon as a reading is finished, so one thumb is enough.
 * The engine works out the window size; the smallest reading of each side is circled.
 */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useMeasure } from "../../api/queries";
import type { Colour, Measure } from "../../api/types";
import { Icon } from "../../components/Icon";
import { Button, Segmented, SizeMark } from "../../components/ui";
import { size } from "../../lib/format";
import {
  HEIGHT_SLOTS,
  SLOT_ORDER,
  cleanDigits,
  complete,
  isFinished,
  nextSlot,
  smallestSlots,
  type Readings,
  type SlotId,
} from "../../lib/readings";

/**
 * Where each slot sits on the opening, in % of the drawing (x, y of its centre). A width slot
 * sits on its horizontal line (its y) and a height slot on its vertical line (its x); no slot
 * sits where two lines cross, so a width can never be read as a height.
 */
const PLACES: Record<SlotId, { x: number; y: number }> = {
  wTop: { x: 70, y: 9 },
  wMiddle: { x: 30, y: 50 },
  wBottom: { x: 70, y: 91 },
  hLeft: { x: 13, y: 30 },
  hMiddle: { x: 50, y: 70 },
  hRight: { x: 87, y: 30 },
};

/** Engine formulas write "2 x 10"; on screen the multiplication sign is ×. */
const times = (formula: string) => formula.replace(/ x /g, " × ");

const WHERE: Record<SlotId, string> = {
  wTop: "top",
  wMiddle: "middle",
  wBottom: "bottom",
  hLeft: "left",
  hMiddle: "middle",
  hRight: "right",
};

export interface MeasureResult {
  readings: { widths: number[]; heights: number[] };
  measure: Measure;
}

export function MeasureStep({
  readings,
  onReadings,
  colour,
  onColour,
  onDone,
  onSkip,
}: {
  readings: Readings;
  onReadings: (next: Readings) => void;
  colour: Colour;
  onColour: (colour: Colour) => void;
  onDone: (result: MeasureResult) => void;
  onSkip: () => void;
}) {
  const { t } = useTranslation();
  const inputs = useRef<Partial<Record<SlotId, HTMLInputElement | null>>>({});
  const [active, setActive] = useState<SlotId>(
    () => SLOT_ORDER.find((slot) => readings[slot] === "") ?? "wTop",
  );
  const [explain, setExplain] = useState(false);
  const measure = useMeasure();
  const { mutate } = measure;
  const values = complete(readings);
  const valuesKey = values ? JSON.stringify(values) : "";
  const smallest = smallestSlots(readings);
  const result = values ? measure.data : undefined;
  const spread = new Set(result?.warnings ?? []);

  useEffect(() => {
    if (valuesKey) {
      mutate({ readings: JSON.parse(valuesKey) as { widths: number[]; heights: number[] }, colour });
    }
  }, [valuesKey, colour, mutate]);

  function type(slot: SlotId, raw: string) {
    const text = cleanDigits(raw);
    onReadings({ ...readings, [slot]: text });
    if (isFinished(text)) {
      const next = nextSlot(slot);
      if (next) inputs.current[next]?.focus();
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col">
      <div className="space-y-3 px-4 pt-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-2xl font-extrabold">{t("position.stepMeasure")}</h2>
          <button
            type="button"
            onClick={onSkip}
            className="min-h-11 shrink-0 text-base font-semibold text-graphite-soft underline decoration-2 underline-offset-4"
          >
            {t("position.skipMeasure")}
          </button>
        </div>
        <Segmented<Colour>
          label={t("position.colour")}
          hideLabel
          value={colour}
          onChange={onColour}
          options={[
            { value: "white", label: t("colours.white") },
            { value: "foil_one_side", label: t("colours.foil_one_side") },
            { value: "foil_both_sides", label: t("colours.foil_both_sides") },
          ]}
        />
      </div>

      <div className="relative mx-auto mt-3 mb-4 aspect-[10/9] w-full max-w-[19.5rem] px-4" data-testid="opening">
        {/* The opening: graphite reveal over hatched masonry; each reading is a dimension string
            with end ticks, across for widths and down for heights. */}
        <div className="absolute inset-x-4 inset-y-0 rounded-sm border-[3px] border-graphite bg-[repeating-linear-gradient(135deg,var(--color-plaster-deep)_0_2px,transparent_2px_11px)]" />
        {SLOT_ORDER.map((slot) => {
          const horizontal = !HEIGHT_SLOTS.includes(slot);
          const place = PLACES[slot];
          const on = active === slot;
          const ink = on ? "bg-chalk before:bg-chalk after:bg-chalk" : "bg-graphite-line before:bg-graphite-line after:bg-graphite-line";
          const ticks = horizontal
            ? "inset-x-[1.6rem] h-0.5 before:absolute before:-top-[5px] before:left-0 before:h-3 before:w-0.5 after:absolute after:-top-[5px] after:right-0 after:h-3 after:w-0.5"
            : "inset-y-2.5 w-0.5 before:absolute before:top-0 before:-left-[5px] before:h-0.5 before:w-3 after:absolute after:bottom-0 after:-left-[5px] after:h-0.5 after:w-3";
          return (
            <span
              key={`line-${slot}`}
              aria-hidden="true"
              className={`absolute ${ink} ${ticks}`}
              style={horizontal ? { top: `${place.y}%` } : { left: `calc(1rem + (100% - 2rem) * ${place.x / 100})` }}
            />
          );
        })}
        {SLOT_ORDER.map((slot) => {
          const place = PLACES[slot];
          const isWidth = !HEIGHT_SLOTS.includes(slot);
          const label = t(isWidth ? "position.widthAt" : "position.heightAt", {
            where: t(`position.${WHERE[slot]}`),
          });
          const warn = spread.has(isWidth ? "width" : "height") && readings[slot] !== "";
          const counts = smallest.has(slot);
          const on = active === slot;
          return (
            <label
              key={slot}
              className="absolute -translate-x-1/2 -translate-y-1/2"
              style={{ left: `calc(1rem + (100% - 2rem) * ${place.x / 100})`, top: `${place.y}%` }}
            >
              <span className="sr-only">{label}</span>
              <input
                ref={(node) => {
                  inputs.current[slot] = node;
                }}
                value={readings[slot]}
                onChange={(event) => type(slot, event.target.value)}
                onFocus={() => setActive(slot)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    const next = nextSlot(slot);
                    if (next) inputs.current[next]?.focus();
                  }
                }}
                inputMode="numeric"
                enterKeyHint={slot === "hRight" ? "done" : "next"}
                autoComplete="off"
                placeholder={t(`position.${WHERE[slot]}`)}
                aria-invalid={warn || undefined}
                className={[
                  "figure h-12 w-[4.75rem] rounded-slot border-2 bg-board text-center text-figure-md outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-sm placeholder:font-semibold placeholder:tracking-normal",
                  on ? "border-chalk text-chalk shadow-[0_0_0_4px_var(--color-chalk-tint)]" : "border-graphite-line",
                  warn ? "border-crayon text-crayon" : "",
                  counts && !on ? "ring-[3px] ring-graphite ring-offset-2 ring-offset-plaster" : "",
                ].join(" ")}
              />
            </label>
          );
        })}
      </div>

      <section
        aria-live="polite"
        className="sticky bottom-0 mt-auto border-t-2 border-plaster-deep bg-board px-4 pt-4 pb-[max(1rem,env(safe-area-inset-bottom))] shadow-sheet"
      >
        <div className="flex min-h-11 items-center justify-between gap-3">
          <p className="text-base font-semibold text-graphite-soft">{t("position.window")}</p>
          {result && (
            <button
              type="button"
              aria-expanded={explain}
              onClick={() => setExplain(!explain)}
              className="min-h-11 text-base font-bold text-chalk underline decoration-2 underline-offset-4"
            >
              {t("position.howCalculated")}
            </button>
          )}
        </div>
        {result ? (
          <>
            <p className="flex items-end gap-2">
              <SizeMark className="text-figure-lg">{size(result.width_mm, result.height_mm)}</SizeMark>
              <span className="figure mb-3 text-figure-md text-graphite-soft">mm</span>
            </p>
            {result.warnings.map((dimension) => (
              <p key={dimension} className="mt-1.5 flex items-center gap-2 font-semibold text-crayon">
                <Icon name="alert" className="size-5 shrink-0" />
                {t("position.spreadWarning", { dimension: t(`position.${dimension}`) })}
              </p>
            ))}
            {explain && (
              <div className="mt-1 space-y-1 rounded-slot bg-plaster p-3">
                <p className="text-sm text-graphite-soft">{t("position.smallestCounts")}</p>
                <p className="figure text-figure-sm">{times(result.formula_width)}</p>
                <p className="figure text-figure-sm">{times(result.formula_height)}</p>
              </div>
            )}
          </>
        ) : (
          <p className="figure text-figure-lg text-graphite-line" aria-hidden="true">
            – × –
          </p>
        )}
        {measure.isError && (
          <p role="alert" className="mt-2 font-semibold text-crayon">
            {measure.error.message}
          </p>
        )}
        <Button
          className="mt-3 w-full"
          icon="forward"
          disabled={!result || !values}
          onClick={() => {
            if (result && values) onDone({ readings: values, measure: result });
          }}
        >
          {t("position.nextType")}
        </Button>
      </section>
    </div>
  );
}
