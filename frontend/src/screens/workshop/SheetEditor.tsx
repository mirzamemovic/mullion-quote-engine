/**
 * A profile system's sheet: the cutting values, the stock bar lengths and every deduction the
 * workshop's window types need (the engine lists them), each with the catalogue page it came
 * from. A test cut runs the real rules on the values as typed, before anything is published.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import { ApiError } from "../../api/client";
import { useMe, useSystems } from "../../api/queries";
import type { ProfileSystem, Sheet } from "../../api/types";
import { useConstructionTypes, useCutPreview, usePublishSheet, useSaveSheetDraft, useSheetFields, useSheets } from "../../api/workshop";
import { ActionError } from "../../components/Reauth";
import { Button, Check, ErrorNote, Field, Loading, Note, Section, Select } from "../../components/ui";
import { workshopLabel } from "../../lib/labels";
import { isOwner, Page } from "./Page";

type Values = Record<string, string>;

function numbers(values: Values): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(values)) {
    if (/^\d{1,5}$/.test(v.trim())) out[k] = Number(v.trim());
  }
  return out;
}

function texts(mapping: unknown): Values {
  const out: Values = {};
  if (mapping && typeof mapping === "object") {
    for (const [k, v] of Object.entries(mapping as Record<string, unknown>)) {
      if (typeof v === "number" || typeof v === "string") out[k] = String(v);
    }
  }
  return out;
}

export function SheetEditor() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const systems = useSystems();
  const sheets = useSheets(id);
  const system = systems.data?.find((s) => s.id === id);
  if (systems.isPending || sheets.isPending) return <Page title={t("sheet.none")} back="/workshop/systems"><Loading /></Page>;
  if (!system || sheets.isError) {
    return <Page title={t("sheet.none")} back="/workshop/systems"><ErrorNote message={sheets.error?.message ?? ""} /></Page>;
  }
  const latest = sheets.data.find((s) => s.status === "draft") ?? sheets.data[0];
  return <Editor key={latest?.id ?? "new"} system={system} sheet={latest} />;
}

function Editor({ system, sheet }: { system: ProfileSystem; sheet: Sheet | undefined }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const owner = isOwner(useMe().data?.role);
  const constants = (sheet?.constants ?? {}) as Record<string, unknown>;
  const [reinforced, setReinforced] = useState<boolean>(
    typeof constants.reinforced === "boolean" ? constants.reinforced : system.material === "pvc",
  );
  const [lengths, setLengths] = useState<Values>(texts(constants));
  const [bars, setBars] = useState<Values>(texts(constants.bar_length_mm));
  const [deductions, setDeductions] = useState<Values>(texts(constants.deductions));
  const [pages, setPages] = useState<Values>(texts(sheet?.source_pages));
  const fields = useSheetFields(system.id, reinforced);
  const save = useSaveSheetDraft(system.id);
  const publish = usePublishSheet(system.id);
  const preview = useCutPreview();
  const types = useConstructionTypes();
  const [type, setType] = useState("single_sash_tilt_turn");
  const [w, setW] = useState("800");
  const [h, setH] = useState("1400");
  const name = `${system.brand} ${system.series}`;

  const body = {
    constants: {
      material: system.material,
      reinforced,
      ...numbers(Object.fromEntries((fields.data?.lengths ?? []).map((k) => [k, lengths[k] ?? ""]))),
      bar_length_mm: numbers(bars),
      deductions: numbers(deductions),
    },
    source_pages: Object.fromEntries(Object.entries(pages).filter(([, v]) => v.trim())),
  };
  const saveThen = (then?: (version: number) => void) =>
    save.mutate(body, { onSuccess: (saved) => then?.(saved.version) });
  const doPublish = () => saveThen((version) => publish.mutate(version));
  const missing = preview.error instanceof ApiError ? preview.error.constant : undefined;

  // One line per value: the length in mm and, beside it, the catalogue page it was copied from.
  const valueRow = (key: string, label: string, value: string, set: (v: string) => void) => (
    <fieldset key={key}>
      <legend className="mb-1.5 text-base font-bold">{label}</legend>
      <div className="grid grid-cols-[1fr_7rem] gap-2">
        <input
          aria-label={label}
          inputMode="numeric"
          value={value}
          disabled={!owner}
          onChange={(e) => set(e.target.value.replace(/\D/g, "").slice(0, 5))}
          className="figure h-14 w-full rounded-slot border-2 border-graphite-line bg-board px-4 text-figure-sm outline-none transition-colors duration-150 focus:border-chalk disabled:text-graphite-soft"
        />
        <input
          aria-label={`${label}: ${t("sheet.page")}`}
          placeholder={t("sheet.page")}
          value={pages[key] ?? ""}
          disabled={!owner}
          onChange={(e) => setPages({ ...pages, [key]: e.target.value.slice(0, 40) })}
          className="h-14 w-full rounded-slot border-2 border-graphite-line bg-board px-3 text-base outline-none transition-colors duration-150 placeholder:text-graphite-soft focus:border-chalk disabled:text-graphite-soft"
        />
      </div>
    </fieldset>
  );

  return (
    <Page title={t("sheet.title", { name })} back="/workshop/systems">
      <p className="text-base text-graphite-soft">{t("sheet.intro")}</p>
      {sheet && (
        <p className="font-bold">
          {sheet.status === "published" ? t("sheet.published", { version: sheet.version }) : t("sheet.draft", { version: sheet.version })}
        </p>
      )}
      <Check label={t("sheet.reinforced")} checked={reinforced} disabled={!owner} onChange={setReinforced} />

      <Section title={t("sheet.lengths")}>
        <div className="space-y-4 rounded-slot bg-board p-4">
          {(fields.data?.lengths ?? []).map((key) =>
            valueRow(key, `${t(`sheet.values.${key}`)} (${t("sheet.mm")})`, lengths[key] ?? "", (v) => setLengths({ ...lengths, [key]: v })),
          )}
        </div>
      </Section>
      <Section title={t("sheet.bars")}>
        <div className="space-y-4 rounded-slot bg-board p-4">
          {(fields.data?.bar_roles ?? []).map((role) =>
            valueRow(`bar.${role}`, `${workshopLabel(role, lang)} (${t("sheet.mm")})`, bars[role] ?? "", (v) => setBars({ ...bars, [role]: v })),
          )}
        </div>
      </Section>
      <Section title={t("sheet.deductions")}>
        <div className="space-y-4 rounded-slot bg-board p-4">
          {(fields.data?.deductions ?? []).map((key) =>
            valueRow(key, `${t(`sheet.deduction.${key}`, { defaultValue: key })} (${t("sheet.mm")})`, deductions[key] ?? "", (v) => setDeductions({ ...deductions, [key]: v })),
          )}
        </div>
      </Section>

      <Section title={t("sheet.testCut")}>
        <p className="text-base text-graphite-soft">{t("sheet.testHint")}</p>
        <div className="grid grid-cols-2 gap-3">
          <Select
            className="col-span-2"
            label={t("position.stepType")}
            value={type}
            onChange={setType}
            options={(types.data ?? []).filter((x) => x.enabled).map((x) => ({ value: x.key, label: t(`types.${x.key}`) }))}
          />
          <Field label={t("position.width")} inputMode="numeric" value={w} onChange={(e) => setW(e.target.value.replace(/\D/g, "").slice(0, 4))} />
          <Field label={t("position.height")} inputMode="numeric" value={h} onChange={(e) => setH(e.target.value.replace(/\D/g, "").slice(0, 4))} />
        </div>
        <Button
          tone="secondary"
          className="w-full"
          busy={preview.isPending}
          onClick={() => preview.mutate({ constants: body.constants, construction_type: type, width_mm: Number(w), height_mm: Number(h) })}
        >
          {t("sheet.testRun")}
        </Button>
        {missing && (
          <Note>
            {t("sheet.missingValue", {
              name: missing.startsWith("deductions.")
                ? t(`sheet.deduction.${missing.slice(11)}`, { defaultValue: missing })
                : t(`sheet.values.${missing}`, { defaultValue: missing }),
            })}
          </Note>
        )}
        {preview.isError && !missing && <ErrorNote message={preview.error.message} />}
        {preview.data && (
          <ul className="divide-y-2 divide-plaster rounded-slot bg-board px-4">
            {[...preview.data.cut_list.pieces, ...preview.data.cut_list.steel].map((p) => (
              <li key={`${p.label}-${p.formula}`} className="py-2">
                <span className="flex items-baseline justify-between gap-3">
                  <span>{workshopLabel(p.label, lang)}</span>
                  <span className="figure text-figure-sm">{p.qty} × {p.length_mm}</span>
                </span>
                <span className="block text-sm text-graphite-soft">{p.formula}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {owner && (
        <div className="space-y-3">
          {save.isSuccess && !publish.isSuccess && <p role="status" className="font-semibold text-tick">{t("sheet.saved")}</p>}
          {publish.isSuccess && <p role="status" className="font-semibold text-tick">{t("sheet.published", { version: publish.data.version })}</p>}
          {save.isError && <ErrorNote message={save.error.message} />}
          <ActionError error={publish.error} retry={doPublish} />
          <Button tone="secondary" className="w-full" busy={save.isPending} onClick={() => saveThen()}>
            {t("sheet.saveDraft")}
          </Button>
          <Button className="w-full" busy={publish.isPending} onClick={doPublish}>
            {t("sheet.publish")}
          </Button>
        </div>
      )}
    </Page>
  );
}
