/**
 * The workshop's own details (name, contact, VAT, currency, language) and its quote settings
 * (margin, VAT rate, advance, validity). Both are saved with a password re-check.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useSaveSettings, useSettings } from "../../api/queries";
import type { Settings, Workshop } from "../../api/types";
import { apiUrl, fileBase64 } from "../../api/client";
import { useRemoveLogo, useSaveLogo, useSaveWorkshop, useWorkshop } from "../../api/workshop";
import { Icon } from "../../components/Icon";
import { ActionError } from "../../components/Reauth";
import { Button, Check, ErrorNote, Field, Loading, Note, Section, Segmented, Select } from "../../components/ui";
import { CURRENCIES } from "../../lib/format";
import { Page } from "./Page";

export function Details() {
  const { t } = useTranslation();
  return (
    <Page title={t("profile.title")}>
      <Profile />
      <Logo />
      <QuoteSettings />
    </Page>
  );
}

const LOGO_TYPES = ["image/png", "image/jpeg"];
const LOGO_MAX_BYTES = 300 * 1024;

/** The logo printed on client quotes. The server checks it again (type, size, pixels). */
function Logo() {
  const { t } = useTranslation();
  const workshop = useWorkshop();
  const save = useSaveLogo();
  const remove = useRemoveLogo();
  // Bumped after an upload so the image is fetched again under a new address.
  const [version, setVersion] = useState(0);
  // Kept until saved, so a password re-check can send the same file again.
  const [file, setFile] = useState<File | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  if (!workshop.data) return null;
  const hasLogo = workshop.data.has_logo ?? false;

  const upload = async (chosen: File) => {
    setProblem(null);
    if (!LOGO_TYPES.includes(chosen.type)) return setProblem(t("logo.wrongType"));
    if (chosen.size > LOGO_MAX_BYTES) return setProblem(t("logo.tooBig"));
    setFile(chosen);
    save.mutate(await fileBase64(chosen), {
      onSuccess: () => {
        setFile(null);
        setVersion((v) => v + 1);
      },
    });
  };

  return (
    <Section title={t("logo.title")}>
      <div className="space-y-3 rounded-slot bg-board p-4">
        {hasLogo ? (
          <img src={`${apiUrl("/workshop/logo")}?v=${version}`} alt={t("logo.current")} className="max-h-20 max-w-full object-contain" />
        ) : (
          <p className="text-graphite-soft">{t("logo.none")}</p>
        )}
        <p className="text-sm text-graphite-soft">{t("logo.hint")}</p>
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="flex min-h-14 cursor-pointer items-center justify-center gap-2 rounded-slot border-2 border-graphite bg-board px-5 text-lg font-bold transition-colors duration-150 hover:bg-plaster has-focus-visible:outline-3 has-focus-visible:outline-chalk">
            <Icon name="plus" />
            {hasLogo ? t("logo.replace") : t("logo.choose")}
            <input
              type="file"
              accept="image/png,image/jpeg"
              className="sr-only"
              disabled={save.isPending}
              onChange={(e) => {
                const chosen = e.target.files?.[0];
                e.target.value = "";
                if (chosen) void upload(chosen);
              }}
            />
          </label>
          {hasLogo && (
            <Button tone="quiet" icon="trash" busy={remove.isPending} onClick={() => remove.mutate()}>
              {t("logo.remove")}
            </Button>
          )}
        </div>
        {problem && <Note>{problem}</Note>}
        <ActionError error={save.error} retry={() => file && void upload(file)} />
        <ActionError error={remove.error} retry={() => remove.mutate()} />
      </div>
    </Section>
  );
}

function Profile() {
  const { t } = useTranslation();
  const workshop = useWorkshop();
  const save = useSaveWorkshop();
  const [draft, setDraft] = useState<Workshop | null>(null);
  const value = draft ?? workshop.data;
  if (workshop.isPending) return <Loading />;
  if (workshop.isError || !value) return <ErrorNote message={workshop.error?.message ?? ""} />;
  const set = (patch: Partial<Workshop>) => setDraft({ ...value, ...patch });
  const submit = () => save.mutate(value, { onSuccess: () => setDraft(null) });

  return (
    <Section title={t("profile.section")}>
      <form
        className="space-y-3 rounded-slot bg-board p-4"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Field label={t("profile.name")} value={value.name} onChange={(e) => set({ name: e.target.value.slice(0, 200) })} />
        <Field label={t("profile.address")} value={value.address ?? ""} onChange={(e) => set({ address: e.target.value.slice(0, 200) })} />
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("profile.phone")} inputMode="tel" value={value.phone ?? ""} onChange={(e) => set({ phone: e.target.value.slice(0, 50) })} />
          <Field label={t("profile.email")} type="email" value={value.email ?? ""} onChange={(e) => set({ email: e.target.value.slice(0, 200) })} />
        </div>
        <Field label={t("profile.vatNumber")} value={value.vat_number ?? ""} onChange={(e) => set({ vat_number: e.target.value.slice(0, 50) })} />
        <Check label={t("profile.vatRegistered")} checked={value.vat_registered ?? false} onChange={(v) => set({ vat_registered: v })} />
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Select
              label={t("profile.currency")}
              value={value.currency ?? "EUR"}
              onChange={(v) => set({ currency: v as Workshop["currency"] })}
              options={CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
            <p className="mt-1.5 text-sm text-graphite-soft">{t("profile.currencyLocked")}</p>
          </div>
          <Select
            label={t("profile.language")}
            value={value.language ?? "en"}
            onChange={(v) => set({ language: v === "bs" ? "bs" : "en" })}
            options={[{ value: "en", label: t("profile.en") }, { value: "bs", label: t("profile.bs") }]}
          />
        </div>
        <ActionError error={save.error} retry={submit} />
        <Button type="submit" busy={save.isPending} disabled={!draft}>
          {t("app.save")}
        </Button>
        {save.isSuccess && !draft && <p role="status" className="font-semibold text-tick">{t("admin.saved")}</p>}
      </form>
    </Section>
  );
}

type PercentKey = "margin_default_bp" | "margin_warn_bp" | "vat_bp" | "advance_bp";
type BarPricing = Settings["bar_pricing"];

const PERCENT_FIELDS: { key: PercentKey; label: string }[] = [
  { key: "margin_default_bp", label: "admin.marginDefault" },
  { key: "margin_warn_bp", label: "admin.marginWarn" },
  { key: "vat_bp", label: "admin.vat" },
  { key: "advance_bp", label: "admin.advance" },
];

/** "25", "18,5" -> basis points, read as text (no float rounding). */
function percentBp(text: string): number | null {
  const match = /^(\d{1,3})(?:[.,](\d{1,2}))?$/.exec(text.trim());
  if (!match) return null;
  const bp = Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
  return bp <= 10_000 ? bp : null;
}

function bpText(bp: number, language: string): string {
  const text = `${Math.trunc(bp / 100)}${bp % 100 ? `.${String(bp % 100).padStart(2, "0").replace(/0$/, "")}` : ""}`;
  return language.startsWith("en") ? text : text.replace(".", ",");
}

function QuoteSettings() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const settings = useSettings();
  const save = useSaveSettings();
  const [texts, setTexts] = useState<Partial<Record<keyof Settings, string>>>({});
  const [barPricing, setBarPricing] = useState<BarPricing | null>(null);
  if (settings.isPending) return <Loading />;
  if (settings.isError) return <ErrorNote message={settings.error.message} />;
  const base = settings.data;
  const value: Settings = { ...base };
  let valid = true;
  for (const { key } of PERCENT_FIELDS) {
    const text = texts[key];
    if (text !== undefined) {
      const bp = percentBp(text);
      if (bp === null) valid = false;
      else value[key] = bp;
    }
  }
  for (const key of ["quote_valid_days", "price_age_warn_days"] as const) {
    const text = texts[key];
    if (text !== undefined) {
      const days = Number(text);
      if (!/^\d{1,3}$/.test(text) || days < 1) valid = false;
      else value[key] = days;
    }
  }
  value.bar_pricing = barPricing ?? base.bar_pricing;
  const byLength = value.bar_pricing === "used_length";
  const wasteText = texts.bar_waste_bp;
  if (byLength) {
    // Used length needs his own waste figure: an empty field is not zero.
    const bp = wasteText === undefined ? (base.bar_waste_bp ?? null) : percentBp(wasteText);
    if (bp === null) valid = false;
    else value.bar_waste_bp = bp;
  }
  const dirty = Object.keys(texts).length > 0 || barPricing !== null;
  const submit = () =>
    save.mutate(value, {
      onSuccess: () => {
        setTexts({});
        setBarPricing(null);
      },
    });
  const shown = (key: keyof Settings, fallback: string) => texts[key] ?? fallback;

  return (
    <Section title={t("hub.settings")}>
      <form
        className="grid grid-cols-2 gap-3 rounded-slot bg-board p-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid) submit();
        }}
      >
        {PERCENT_FIELDS.map(({ key, label }) => (
          <Field
            key={key}
            label={t(label)}
            inputMode="decimal"
            value={shown(key, bpText(base[key], lang))}
            onChange={(e) => setTexts({ ...texts, [key]: e.target.value.replace(/[^\d,.]/g, "") })}
            error={texts[key] !== undefined && percentBp(texts[key]) === null ? t("errors.range", { min: 0, max: 100 }) : undefined}
          />
        ))}
        <Field label={t("admin.validDays")} inputMode="numeric" value={shown("quote_valid_days", String(base.quote_valid_days))} onChange={(e) => setTexts({ ...texts, quote_valid_days: e.target.value.replace(/\D/g, "").slice(0, 3) })} />
        <Field label={t("admin.priceAge")} inputMode="numeric" value={shown("price_age_warn_days", String(base.price_age_warn_days))} onChange={(e) => setTexts({ ...texts, price_age_warn_days: e.target.value.replace(/\D/g, "").slice(0, 3) })} />
        <div className="col-span-2 space-y-2">
          <Segmented<BarPricing>
            label={t("admin.barPricing")}
            value={value.bar_pricing}
            onChange={setBarPricing}
            wrap
            options={[
              { value: "whole_bars", label: t("admin.wholeBars") },
              { value: "used_length", label: t("admin.usedLength") },
            ]}
          />
          <p className="text-sm text-graphite-soft">{t(byLength ? "admin.usedLengthHint" : "admin.wholeBarsHint")}</p>
        </div>
        {byLength && (
          <Field
            label={t("admin.barWaste")}
            inputMode="decimal"
            value={wasteText ?? (base.bar_waste_bp != null ? bpText(base.bar_waste_bp, lang) : "")}
            onChange={(e) => setTexts({ ...texts, bar_waste_bp: e.target.value.replace(/[^\d,.]/g, "") })}
            hint={t("admin.barWasteHint")}
            error={wasteText !== undefined && percentBp(wasteText) === null ? t("errors.range", { min: 0, max: 100 }) : undefined}
          />
        )}
        <div className="col-span-2 space-y-2">
          <ActionError error={save.error} retry={submit} />
          <Button type="submit" busy={save.isPending} disabled={!dirty || !valid}>
            {t("app.save")}
          </Button>
          {save.isSuccess && !dirty && <p role="status" className="font-semibold text-tick">{t("admin.saved")}</p>}
        </div>
      </form>
    </Section>
  );
}
