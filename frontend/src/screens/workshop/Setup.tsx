/**
 * The setup checklist: what the workshop still has to enter before it can quote, asked of the
 * engine itself (GET /setup/status). Each line opens the screen that fixes it.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { apiUrl } from "../../api/client";
import { useMe } from "../../api/queries";
import { useSetupStatus, useStarterPrices } from "../../api/workshop";
import { ActionError } from "../../components/Reauth";
import { Button, Check, ErrorNote, LinkRow, Loading, Note, Section } from "../../components/ui";
import { workshopLabel } from "../../lib/labels";
import { Page } from "./Page";

export function Setup() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const me = useMe().data;
  const status = useSetupStatus();
  const starter = useStarterPrices();
  const navigate = useNavigate();
  const [withSystems, setWithSystems] = useState(true);

  if (status.isPending) return <Page title={t("setup.title")}><Loading /></Page>;
  if (status.isError) return <Page title={t("setup.title")}><ErrorNote message={status.error.message} /></Page>;
  const s = status.data;
  const missing = s.prices_missing.length;
  const total = s.prices_needed;
  const pricesTo = s.price_list_id ? `/workshop/prices/${s.price_list_id}` : "/workshop/prices";
  const startStarter = () =>
    starter.mutate(withSystems, { onSuccess: (list) => void navigate(`/workshop/prices/${list.id}`) });

  return (
    <Page title={t("setup.title")}>
      <p className="text-lg font-bold">{s.ready ? t("setup.ready") : t("setup.left", { percent: s.percent })}</p>

      <div className="space-y-3">
        <LinkRow to="/workshop/prices" title={t("setup.suppliers")} done={s.suppliers > 0} />
        {s.systems.length === 0 && <LinkRow to="/workshop/systems" title={t("setup.noSystems")} done={false} />}
        {s.systems.map((system) => (
          <LinkRow
            key={system.id}
            to={`/workshop/systems/${system.id}`}
            title={t("setup.sheet", { name: system.name })}
            done={system.done}
            status={
              system.problem ??
              (system.missing.length
                ? t("setup.valuesMissing", { count: system.missing.length })
                : system.sheet === "published"
                  ? t("setup.sheetDone")
                  : system.sheet === "draft"
                    ? t("setup.sheetDraft")
                    : t("setup.sheetMissing"))
            }
          />
        ))}
        <LinkRow
          to={pricesTo}
          title={t("setup.prices")}
          done={s.price_list_id !== null && missing === 0}
          status={
            s.price_list_id === null
              ? t("setup.noPriceList")
              : missing
                ? t("setup.pricesMissing", { count: missing, total })
                : t("setup.pricesDone", { total })
          }
        />
        <LinkRow to={pricesTo} title={t("setup.glass")} done={s.glass_priced} />
      </div>

      {missing > 0 && (
        <ul className="space-y-1 rounded-slot bg-board p-4 text-base">
          {s.prices_missing.slice(0, 8).map((p) => (
            <li key={`${p.kind}/${p.ref}/${p.colour ?? ""}`}>
              {workshopLabel(`${p.kind} ${p.ref}`, lang)}
              {p.colour ? ` · ${t(`colours.${p.colour}`)}` : ""}
            </li>
          ))}
          {missing > 8 && <li className="text-graphite-soft">…</li>}
        </ul>
      )}

      {s.foil_prices_missing.length > 0 && <Note tone="hint">{t("setup.foil", { count: s.foil_prices_missing.length })}</Note>}
      {s.estimates > 0 && <Note>{t("setup.estimates", { count: s.estimates })}</Note>}
      {s.openings_without_hardware_set.length > 0 && (
        <Note tone="hint">
          {t("setup.noHardware", { openings: s.openings_without_hardware_set.map((o) => t(`openings.${o}`)).join(", ") })}
        </Note>
      )}

      {missing > 0 && (
        <a
          href={apiUrl(`/setup/price-template.csv${s.price_list_id ? `?price_list_id=${s.price_list_id}` : ""}`)}
          className="flex min-h-14 items-center justify-center rounded-slot border-2 border-graphite bg-board px-5 text-lg font-bold transition-colors duration-150 hover:bg-plaster"
        >
          {t("setup.template")}
        </a>
      )}

      {s.price_list_id === null && (
        <Section title={t("setup.starter")}>
          <p className="text-base text-graphite-soft">{t("setup.starterHint")}</p>
          {me?.currency === "EUR" ? (
            <>
              <Check label={t("setup.starterSystems")} checked={withSystems} onChange={setWithSystems} />
              <Button className="w-full" busy={starter.isPending} onClick={startStarter}>
                {t("setup.starter")}
              </Button>
              <ActionError error={starter.error} retry={startStarter} />
            </>
          ) : (
            <Note tone="hint">{t("setup.starterEuro")}</Note>
          )}
        </Section>
      )}
    </Page>
  );
}
