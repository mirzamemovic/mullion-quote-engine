/** The workshop menu: everything that is not a quote, one row each, with its state under it. */
import { useTranslation } from "react-i18next";

import { useLogout, useMe } from "../../api/queries";
import { useSetupStatus } from "../../api/workshop";
import { Button, LanguageToggle, LinkRow, TopBar } from "../../components/ui";
import { isOwner } from "./Page";

export function Hub() {
  const { t } = useTranslation();
  const me = useMe().data;
  const owner = isOwner(me?.role);
  const setup = useSetupStatus();
  const logout = useLogout();
  const ready = setup.data?.ready;

  return (
    <>
      <TopBar title={t("hub.title")} subtitle={me?.workshop_name} back="/" actions={<LanguageToggle className="text-white" />} />
      <main className="mx-auto max-w-3xl space-y-3 px-4 pt-5 pb-16">
        {owner && (
          <LinkRow
            to="/workshop/setup"
            title={t("hub.setup")}
            status={setup.data ? (ready ? t("hub.ready") : t("hub.percent", { percent: setup.data.percent })) : undefined}
            done={setup.data ? ready : undefined}
          />
        )}
        <LinkRow to="/workshop/systems" title={t("hub.systems")} />
        <LinkRow to="/workshop/prices" title={t("hub.prices")} />
        {owner && <LinkRow to="/workshop/team" title={t("hub.team")} />}
        {owner && <LinkRow to="/workshop/details" title={t("hub.details")} status={t("hub.settings")} />}
        <LinkRow to="/workshop/account" title={t("hub.account")} status={me?.email} />
        <Button tone="secondary" icon="logout" className="mt-5 w-full" busy={logout.isPending} onClick={() => logout.mutate()}>
          {t("app.logout")}
        </Button>
      </main>
    </>
  );
}
