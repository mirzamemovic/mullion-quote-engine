/**
 * Prices and settings at the workshop PC: the current price list, a supplier's price change as a
 * new version, and the quote settings. Changing prices asks for the password again (step-up).
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import {
  useBump,
  useLogout,
  usePriceLists,
  useReauth,
  useSaveSettings,
  useSettings,
  useSuppliers,
} from "../api/queries";
import type { Settings } from "../api/types";
import { Button, ErrorNote, Field, Loading, TopBar } from "../components/ui";
import { day, euros, isoDate } from "../lib/format";
import { unitLabel, workshopLabel } from "../lib/labels";

function needsReauth(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403 && /password/i.test(error.message);
}

function Reauth({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const reauth = useReauth();
  const [password, setPassword] = useState("");
  return (
    <form
      className="mt-3 space-y-3 rounded-slot bg-chalk-tint p-4"
      onSubmit={(e) => {
        e.preventDefault();
        reauth.mutate(password, { onSuccess: onDone });
      }}
    >
      <p className="font-bold">{t("admin.reauthTitle")}</p>
      <p className="text-base text-graphite-soft">{t("admin.reauthHint")}</p>
      <Field label={t("login.password")} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} error={reauth.isError ? t("login.wrong") : undefined} />
      <Button type="submit" busy={reauth.isPending} disabled={!password}>
        {t("admin.reauthSubmit")}
      </Button>
    </form>
  );
}

export function Admin() {
  const { t } = useTranslation();
  const logout = useLogout();
  return (
    <>
      <TopBar title={t("admin.title")} back="/" />
      <main className="mx-auto max-w-3xl space-y-8 px-4 pt-5 pb-16">
        <Prices />
        <QuoteSettings />
        <Button tone="secondary" icon="logout" className="w-full" busy={logout.isPending} onClick={() => logout.mutate()}>
          {t("app.logout")}
        </Button>
      </main>
    </>
  );
}

function Prices() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const lists = usePriceLists();
  const suppliers = useSuppliers();
  const bump = useBump();
  const [supplierId, setSupplierId] = useState("");
  const [percent, setPercent] = useState("");
  const [validFrom, setValidFrom] = useState(isoDate(new Date()));
  const current = lists.data?.[0];
  const bp = Math.round(Number(percent.replace(",", ".")) * 100);
  const ready = current && supplierId && Number.isFinite(bp) && bp !== 0 && percent !== "";
  const names = new Map((suppliers.data ?? []).map((s) => [s.id, s.name]));

  function submit() {
    if (!current) return;
    bump.mutate({ listId: current.id, body: { supplier_id: supplierId, bp, valid_from: validFrom } }, { onSuccess: () => setPercent("") });
  }

  return (
    <section aria-labelledby="prices">
      <h2 id="prices" className="text-2xl font-extrabold">
        {t("admin.prices")}
      </h2>
      {lists.isPending && <Loading />}
      {lists.isError && <ErrorNote message={lists.error.message} />}
      {current && (
        <div className="mt-3 rounded-slot bg-board p-4">
          <p className="text-lg font-bold">{t("admin.validFrom", { date: day(current.valid_from, lang) })}</p>
          <p className="text-base text-graphite-soft">
            {current.note} · {t("admin.entries", { count: current.entries.length })}
          </p>
          <ul className="mt-3 max-h-96 overflow-y-auto" tabIndex={0} aria-label={t("admin.prices")}>
            {current.entries.map((e) => (
              <li key={e.id} className="flex items-baseline justify-between gap-3 border-t border-plaster py-2">
                <span className="min-w-0">
                  <span className="block">
                    {workshopLabel(`${e.item_kind} ${e.item_ref}`, lang)}
                    {e.colour ? ` · ${t(`colours.${e.colour}`)}` : ""}
                  </span>
                  <span className="block truncate text-sm text-graphite-soft">{names.get(e.supplier_id) ?? ""}</span>
                </span>
                <span className="shrink-0 text-right">
                  <span className="figure block text-figure-sm">{euros(e.amount_cents, lang)}</span>
                  <span className="block text-sm text-graphite-soft">/ {unitLabel(e.unit, lang)}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {current && (
        <form
          className="mt-4 space-y-3 rounded-slot bg-board p-4"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <h3 className="text-lg font-extrabold">{t("admin.bump")}</h3>
          <label className="block">
            <span className="mb-1.5 block text-base font-bold">{t("admin.bumpSupplier")}</span>
            <select
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              className="h-14 w-full rounded-slot border-2 border-graphite-line bg-board px-3 text-lg focus:border-chalk"
            >
              <option value="">–</option>
              {(suppliers.data ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("admin.bumpPercent")} inputMode="decimal" value={percent} onChange={(e) => setPercent(e.target.value.replace(/[^\d,.-]/g, ""))} />
            <Field label={t("admin.bumpDate")} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
          </div>
          {bump.isError && !needsReauth(bump.error) && <ErrorNote message={bump.error.message} />}
          {needsReauth(bump.error) ? (
            <Reauth onDone={submit} />
          ) : (
            <Button type="submit" busy={bump.isPending} disabled={!ready}>
              {t("admin.bumpSubmit")}
            </Button>
          )}
          {bump.isSuccess && <p role="status" className="font-semibold text-tick">{t("admin.saved")}</p>}
        </form>
      )}
    </section>
  );
}

const PERCENT_FIELDS: { key: keyof Settings; label: string }[] = [
  { key: "margin_default_bp", label: "admin.marginDefault" },
  { key: "margin_warn_bp", label: "admin.marginWarn" },
  { key: "vat_bp", label: "admin.vat" },
  { key: "advance_bp", label: "admin.advance" },
];

function QuoteSettings() {
  const { t } = useTranslation();
  const settings = useSettings();
  const save = useSaveSettings();
  const [draft, setDraft] = useState<Settings | null>(null);
  const value = draft ?? settings.data;
  if (settings.isPending) return <Loading />;
  if (settings.isError || !value) return <ErrorNote message={settings.error?.message ?? ""} />;
  const set = (key: keyof Settings, v: number) => setDraft({ ...value, [key]: v });

  return (
    <section aria-labelledby="settings">
      <h2 id="settings" className="text-2xl font-extrabold">
        {t("admin.settings")}
      </h2>
      <form
        className="mt-3 grid grid-cols-2 gap-3 rounded-slot bg-board p-4"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(value, { onSuccess: () => setDraft(null) });
        }}
      >
        {PERCENT_FIELDS.map(({ key, label }) => (
          <Field
            key={key}
            label={t(label)}
            inputMode="decimal"
            value={String(value[key] / 100).replace(".", ",")}
            onChange={(e) => {
              const n = Math.round(Number(e.target.value.replace(",", ".").replace(/[^\d.]/g, "")) * 100);
              if (Number.isFinite(n)) set(key, Math.min(10_000, Math.max(0, n)));
            }}
          />
        ))}
        <Field label={t("admin.validDays")} inputMode="numeric" value={String(value.quote_valid_days)} onChange={(e) => set("quote_valid_days", Number(e.target.value.replace(/\D/g, "").slice(0, 3)) || 1)} />
        <Field label={t("admin.priceAge")} inputMode="numeric" value={String(value.price_age_warn_days)} onChange={(e) => set("price_age_warn_days", Number(e.target.value.replace(/\D/g, "").slice(0, 3)) || 1)} />
        {save.isError && !needsReauth(save.error) && <div className="col-span-2"><ErrorNote message={save.error.message} /></div>}
        <div className="col-span-2">
          {needsReauth(save.error) ? (
            <Reauth onDone={() => save.mutate(value, { onSuccess: () => setDraft(null) })} />
          ) : (
            <Button type="submit" busy={save.isPending} disabled={!draft}>
              {t("app.save")}
            </Button>
          )}
          {save.isSuccess && !draft && <p role="status" className="mt-2 font-semibold text-tick">{t("admin.saved")}</p>}
        </div>
      </form>
    </section>
  );
}
