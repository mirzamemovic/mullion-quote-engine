/** Opening side per field, glass, quantity and installation. The drawing updates as he taps. */
import { useTranslation } from "react-i18next";

import type { Colour, Opening, PositionIn } from "../../api/types";
import { Icon } from "../../components/Icon";
import { Button, Field, SizeMark } from "../../components/ui";
import { WindowDrawing, fieldCount } from "../../components/WindowDrawing";
import { size } from "../../lib/format";

const OPENING_CHOICES: Opening[] = ["tilt_turn_left", "tilt_turn_right", "turn_left", "turn_right"];
type Installation = NonNullable<PositionIn["installation"]>;
const SWITCHES: { key: keyof Installation; label: string }[] = [
  { key: "install", label: "position.install" },
  { key: "ral", label: "position.ral" },
  { key: "old_window_removal", label: "position.oldWindow" },
  { key: "wall_repair", label: "position.wallRepair" },
];

export interface Details {
  ref: string;
  width: number;
  height: number;
  openings: Opening[];
  glass: string;
  qty: number;
  installation: Installation;
}

export function DetailsStep({
  type,
  colour,
  details,
  glassBuilds,
  sizeEditable,
  busy,
  error,
  onChange,
  onSave,
}: {
  type: string;
  colour: Colour;
  details: Details;
  glassBuilds: string[];
  sizeEditable: boolean;
  busy: boolean;
  error: string | null;
  onChange: (next: Details) => void;
  onSave: () => void;
}) {
  const { t } = useTranslation();
  const fields = fieldCount(type);
  const sizeOk = [details.width, details.height].every((v) => v >= 300 && v <= 3500);
  const set = <K extends keyof Details>(key: K, value: Details[K]) =>
    onChange({ ...details, [key]: value });

  return (
    <div className="pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <div className="sticky top-16 z-10 border-b-2 border-plaster-deep bg-plaster/95 px-4 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <WindowDrawing
            type={type}
            width={details.width}
            height={details.height}
            openings={details.openings}
            colour={colour}
            className="h-24 w-24 shrink-0"
            stroke={1.5}
            title={t(`types.${type}`)}
          />
          <div className="min-w-0">
            <p className="text-base font-bold">{t(`types.${type}`)}</p>
            <p className="flex items-end gap-1.5">
              <SizeMark className="text-figure-md">{size(details.width, details.height)}</SizeMark>
              <span className="figure mb-2.5 text-figure-sm text-graphite-soft">mm</span>
            </p>
            <p className="text-sm text-graphite-soft">
              {t("position.pieces", { count: details.qty })} · {details.glass}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-7 px-4 pt-5">
        <h2 className="text-2xl font-extrabold">{t("position.stepDetails")}</h2>

        {sizeEditable && (
          <div className="grid grid-cols-2 gap-3">
            <Field
              label={t("position.width")}
              inputMode="numeric"
              value={details.width || ""}
              onChange={(e) => set("width", Number(e.target.value.replace(/\D/g, "").slice(0, 4)))}
              error={details.width && !sizeOk ? t("position.sizeLimits") : undefined}
            />
            <Field
              label={t("position.height")}
              inputMode="numeric"
              value={details.height || ""}
              onChange={(e) => set("height", Number(e.target.value.replace(/\D/g, "").slice(0, 4)))}
            />
          </div>
        )}

        {type !== "fixed" &&
          Array.from({ length: fields }, (_, field) => (
            <fieldset key={field}>
              <legend className="mb-2 text-base font-bold">
                {fields > 1 ? `${t("position.opening")} · ${t("position.field", { n: field + 1 })}` : t("position.opening")}
              </legend>
              <div className="grid grid-cols-4 gap-2">
                {OPENING_CHOICES.map((opening) => {
                  const chosen = details.openings[field] === opening;
                  return (
                    <button
                      key={opening}
                      type="button"
                      aria-pressed={chosen}
                      aria-label={t(`openings.${opening}`)}
                      title={t(`openings.${opening}`)}
                      onClick={() => {
                        const next = [...details.openings];
                        next[field] = opening;
                        set("openings", next);
                      }}
                      className={`rounded-slot p-1.5 transition-colors duration-150 ${chosen ? "bg-chalk-tint outline-3 outline-chalk" : "bg-board hover:bg-chalk-tint/60"}`}
                    >
                      <WindowDrawing type="single_sash_tilt_turn" width={700} height={1000} openings={[opening]} className="h-20 w-full" />
                    </button>
                  );
                })}
              </div>
              <p className="mt-1.5 text-sm font-semibold text-graphite-soft">
                {t(`openings.${details.openings[field] ?? "fixed"}`)}
              </p>
            </fieldset>
          ))}

        <fieldset>
          <legend className="mb-2 text-base font-bold">{t("position.glass")}</legend>
          <div className="flex flex-wrap gap-2">
            {glassBuilds.map((build) => (
              <button
                key={build}
                type="button"
                aria-pressed={details.glass === build}
                onClick={() => set("glass", build)}
                className={`figure min-h-12 rounded-slot px-4 text-figure-sm transition-colors duration-150 ${details.glass === build ? "bg-chalk text-white" : "bg-board text-graphite hover:bg-chalk-tint"}`}
              >
                {build}
              </button>
            ))}
          </div>
        </fieldset>

        <div>
          <p className="mb-2 text-base font-bold" id="qty-label">
            {t("position.qty")}
          </p>
          <div className="flex items-center gap-3" role="group" aria-labelledby="qty-label">
            <button
              type="button"
              aria-label="−1"
              disabled={details.qty <= 1}
              onClick={() => set("qty", details.qty - 1)}
              className="grid size-14 place-items-center rounded-slot border-2 border-graphite bg-board disabled:border-graphite-line disabled:text-graphite-line"
            >
              <Icon name="minus" />
            </button>
            <output className="figure w-14 text-center text-figure-lg" aria-live="polite">
              {details.qty}
            </output>
            <button
              type="button"
              aria-label="+1"
              disabled={details.qty >= 99}
              onClick={() => set("qty", details.qty + 1)}
              className="grid size-14 place-items-center rounded-slot border-2 border-graphite bg-board disabled:border-graphite-line"
            >
              <Icon name="plus" />
            </button>
          </div>
        </div>

        <fieldset>
          <legend className="mb-2 text-base font-bold">{t("position.install")}</legend>
          <div className="flex flex-wrap gap-2">
            {SWITCHES.map(({ key, label }) => {
              const on = details.installation[key] ?? key === "install";
              const disabled = key !== "install" && !(details.installation.install ?? true);
              const pressed = on && !disabled;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={pressed}
                  disabled={disabled}
                  onClick={() => set("installation", { ...details.installation, [key]: !on })}
                  className={`inline-flex min-h-12 items-center gap-2 rounded-full px-4 text-base font-bold transition-colors duration-150 disabled:opacity-45 ${pressed ? "bg-chalk text-white" : "border-2 border-graphite-line bg-board text-graphite hover:bg-chalk-tint"}`}
                >
                  <Icon name={pressed ? "check" : "plus"} className="size-5" />
                  {t(label)}
                </button>
              );
            })}
          </div>
        </fieldset>

        <Field
          label={t("position.name")}
          value={details.ref}
          maxLength={50}
          onChange={(e) => set("ref", e.target.value)}
        />

        {error && (
          <p role="alert" className="flex items-start gap-2 rounded-slot bg-crayon-tint p-3 font-semibold">
            <Icon name="alert" className="mt-0.5 size-5 shrink-0 text-crayon" />
            {error}
          </p>
        )}

        <Button
          className="w-full"
          icon="check"
          busy={busy}
          disabled={!sizeOk || !details.ref.trim() || !details.glass}
          onClick={onSave}
        >
          {t("position.done")}
        </Button>
      </div>
    </div>
  );
}
