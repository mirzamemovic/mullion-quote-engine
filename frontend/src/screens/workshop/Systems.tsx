/**
 * The workshop's catalogue: its profile systems (each opens its sheet), the window types it
 * sells, and its hardware sets with their size limits. Staff read it; the owner changes it.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useMe, useSystems } from "../../api/queries";
import type { HardwareSetIn, Opening } from "../../api/types";
import {
  useAddHardwareSet,
  useConstructionTypes,
  useCreateSystem,
  useDeleteHardwareSet,
  useHardwareSets,
  useSetConstructionType,
  useSetupStatus,
} from "../../api/workshop";
import { ActionError } from "../../components/Reauth";
import { Button, Check, ErrorNote, Field, IconButton, LinkRow, Loading, Section, Select } from "../../components/ui";
import { isOwner, Page } from "./Page";

const OPENINGS: Opening[] = ["tilt_turn_left", "tilt_turn_right", "turn_left", "turn_right"];

export function Systems() {
  const { t } = useTranslation();
  const owner = isOwner(useMe().data?.role);
  const systems = useSystems();
  const setup = useSetupStatus();
  const checks = new Map((setup.data?.systems ?? []).map((c) => [c.id, c]));

  return (
    <Page title={t("systems.title")}>
      <section className="space-y-3">
        {systems.isPending && <Loading />}
        {systems.isError && <ErrorNote message={systems.error.message} />}
        {systems.data?.length === 0 && <p className="text-graphite-soft">{t("setup.noSystems")}</p>}
        {systems.data?.map((s) => {
          const check = checks.get(s.id);
          return (
            <LinkRow
              key={s.id}
              to={`/workshop/systems/${s.id}`}
              title={`${s.brand} ${s.series}`}
              status={`${t(`systems.${s.material}`)} · ${s.depth_mm} mm${check ? ` · ${check.missing.length ? t("setup.valuesMissing", { count: check.missing.length }) : t(check.sheet === "published" ? "setup.sheetDone" : check.sheet === "draft" ? "setup.sheetDraft" : "setup.sheetMissing")}` : ""}`}
              done={check?.done}
            />
          );
        })}
      </section>
      {owner && <AddSystem />}
      <WindowTypes owner={owner} />
      <HardwareSets owner={owner} />
    </Page>
  );
}

function AddSystem() {
  const { t } = useTranslation();
  const create = useCreateSystem();
  const [brand, setBrand] = useState("");
  const [series, setSeries] = useState("");
  const [key, setKey] = useState("");
  const [material, setMaterial] = useState<"pvc" | "aluminium">("pvc");
  const [depth, setDepth] = useState("");
  const suggested = `${brand} ${series}`.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const finalKey = key || suggested;
  const depthMm = Number(depth);
  const ready = brand && series && finalKey && depthMm >= 40 && depthMm <= 150;

  return (
    <Section title={t("systems.add")}>
      <form
        className="grid grid-cols-2 gap-3 rounded-slot bg-board p-4"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(
            { key: finalKey, brand, series, material, depth_mm: depthMm, enabled: true },
            { onSuccess: () => { setBrand(""); setSeries(""); setKey(""); setDepth(""); } },
          );
        }}
      >
        <Field label={t("systems.brand")} value={brand} onChange={(e) => setBrand(e.target.value)} />
        <Field label={t("systems.series")} value={series} onChange={(e) => setSeries(e.target.value)} />
        <Field className="col-span-2" label={t("systems.key")} hint={t("systems.keyHint")} value={key || suggested} onChange={(e) => setKey(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} />
        <Select
          label={t("systems.material")}
          value={material}
          onChange={(v) => setMaterial(v === "aluminium" ? "aluminium" : "pvc")}
          options={[{ value: "pvc", label: t("systems.pvc") }, { value: "aluminium", label: t("systems.aluminium") }]}
        />
        <Field label={t("systems.depth")} inputMode="numeric" value={depth} onChange={(e) => setDepth(e.target.value.replace(/\D/g, "").slice(0, 3))} />
        {create.isError && <div className="col-span-2"><ErrorNote message={create.error.message} /></div>}
        <Button type="submit" className="col-span-2" busy={create.isPending} disabled={!ready}>
          {t("systems.add")}
        </Button>
      </form>
    </Section>
  );
}

function WindowTypes({ owner }: { owner: boolean }) {
  const { t } = useTranslation();
  const types = useConstructionTypes();
  const set = useSetConstructionType();
  return (
    <Section title={t("systems.types")}>
      <div className="rounded-slot bg-board p-3">
        {types.data?.map((type) => (
          <Check
            key={type.key}
            label={t(`types.${type.key}`)}
            checked={type.enabled}
            disabled={!owner || set.isPending}
            onChange={(enabled) => set.mutate({ key: type.key, enabled })}
          />
        ))}
      </div>
      {set.isError && <ErrorNote message={set.error.message} />}
    </Section>
  );
}

function HardwareSets({ owner }: { owner: boolean }) {
  const { t } = useTranslation();
  const sets = useHardwareSets();
  const add = useAddHardwareSet();
  const remove = useDeleteHardwareSet();
  const [pending, setPending] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [opening, setOpening] = useState<Opening>("tilt_turn_left");
  const [w, setW] = useState("");
  const [h, setH] = useState("");
  const [area, setArea] = useState("");
  const [kg, setKg] = useState("");
  // Area in m² with up to two decimals, as exact mm²: "2,4" -> 2 400 000.
  const areaMatch = /^(\d{1,2})(?:[.,](\d{1,2}))?$/.exec(area.trim());
  const areaMm2 = areaMatch ? Number(areaMatch[1]) * 1_000_000 + Number((areaMatch[2] ?? "").padEnd(2, "0")) * 10_000 : 0;
  const body: HardwareSetIn = { name, opening_type: opening, max_width_mm: Number(w), max_height_mm: Number(h), max_area_mm2: areaMm2, max_weight_g: Number(kg) * 1000 };
  const ready = name && Number(w) > 0 && Number(h) > 0 && areaMm2 > 0 && Number(kg) > 0;
  const deleteSet = (id: string) => {
    setPending(id);
    remove.mutate(id);
  };

  return (
    <Section title={t("systems.hardware")}>
      <ul className="space-y-2">
        {sets.data?.length === 0 && <li className="text-graphite-soft">{t("systems.none")}</li>}
        {sets.data?.map((set) => (
          <li key={set.id} className="flex items-center gap-3 rounded-slot bg-board px-4 py-3">
            <span className="min-w-0 flex-1">
              <span className="block font-bold">{set.name}</span>
              <span className="block text-sm text-graphite-soft">
                {t(`openings.${set.opening_type}`)} ·{" "}
                {t("systems.hwLimits", {
                  w: set.max_width_mm,
                  h: set.max_height_mm,
                  area: (set.max_area_mm2 / 1_000_000).toFixed(2),
                  kg: Math.round(set.max_weight_g / 1000),
                })}
              </span>
            </span>
            {owner && <IconButton icon="trash" label={t("app.remove")} className="text-crayon hover:bg-crayon-tint" onClick={() => deleteSet(set.id)} />}
          </li>
        ))}
      </ul>
      <ActionError error={remove.error} retry={() => pending && deleteSet(pending)} />
      {owner && (
        <form
          className="grid grid-cols-2 gap-3 rounded-slot bg-board p-4"
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate(body, { onSuccess: () => { setName(""); setW(""); setH(""); setArea(""); setKg(""); } });
          }}
        >
          <h3 className="col-span-2 text-lg font-extrabold">{t("systems.hardwareAdd")}</h3>
          <Field className="col-span-2" label={t("systems.hwName")} value={name} onChange={(e) => setName(e.target.value)} />
          <Select className="col-span-2" label={t("systems.hwOpening")} value={opening} onChange={(v) => setOpening(v as Opening)} options={OPENINGS.map((o) => ({ value: o, label: t(`openings.${o}`) }))} />
          <Field label={t("systems.hwMaxW")} inputMode="numeric" value={w} onChange={(e) => setW(e.target.value.replace(/\D/g, "").slice(0, 4))} />
          <Field label={t("systems.hwMaxH")} inputMode="numeric" value={h} onChange={(e) => setH(e.target.value.replace(/\D/g, "").slice(0, 4))} />
          <Field label={t("systems.hwMaxArea")} inputMode="decimal" value={area} onChange={(e) => setArea(e.target.value.replace(/[^\d,.]/g, ""))} />
          <Field label={t("systems.hwMaxWeight")} inputMode="numeric" value={kg} onChange={(e) => setKg(e.target.value.replace(/\D/g, "").slice(0, 3))} />
          {add.isError && <div className="col-span-2"><ErrorNote message={add.error.message} /></div>}
          <Button type="submit" className="col-span-2" busy={add.isPending} disabled={!ready}>
            {t("systems.hardwareAdd")}
          </Button>
        </form>
      )}
    </Section>
  );
}
