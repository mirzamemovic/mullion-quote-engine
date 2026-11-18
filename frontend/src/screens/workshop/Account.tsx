/**
 * The person's own login: a new password (other devices are logged out) and two-step login,
 * which each person turns on for themselves. The secret is shown once, as text and as an
 * ``otpauth://`` link the phone's authenticator app opens.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api/client";
import { useMe } from "../../api/queries";
import type { TotpSetup } from "../../api/types";
import { useChangePassword, useTotpDisable, useTotpEnable, useTotpSetup } from "../../api/workshop";
import { ActionError } from "../../components/Reauth";
import { Button, Field, Note, Section } from "../../components/ui";
import { Page } from "./Page";

export function Account() {
  const { t } = useTranslation();
  return (
    <Page title={t("account.title")}>
      <Password />
      <TwoStep />
    </Page>
  );
}

function Password() {
  const { t } = useTranslation();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const tooShort = next.length > 0 && next.length < 12;
  const failure = change.error instanceof ApiError && change.error.status === 401 ? t("login.wrong") : change.error?.message;

  return (
    <Section title={t("account.password")}>
      <form
        className="space-y-3 rounded-slot bg-board p-4"
        onSubmit={(e) => {
          e.preventDefault();
          change.mutate({ current_password: current, new_password: next }, { onSuccess: () => { setCurrent(""); setNext(""); } });
        }}
      >
        <Field label={t("account.current")} type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        <Field label={t("account.new")} type="password" autoComplete="new-password" hint={t("join.passwordHint")} value={next} onChange={(e) => setNext(e.target.value)} error={tooShort ? t("join.passwordHint") : undefined} />
        {failure && <Note>{failure}</Note>}
        {change.isSuccess && <p role="status" className="font-semibold text-tick">{t("account.changed")}</p>}
        <Button type="submit" busy={change.isPending} disabled={!current || next.length < 12}>
          {t("account.password")}
        </Button>
      </form>
    </Section>
  );
}

function TwoStep() {
  const { t } = useTranslation();
  const me = useMe().data;
  const setup = useTotpSetup();
  const enable = useTotpEnable();
  const disable = useTotpDisable();
  const [pending, setPending] = useState<TotpSetup | null>(null);
  const [code, setCode] = useState("");
  const on = me?.totp_enabled ?? false;
  const begin = () => setup.mutate(undefined, { onSuccess: setPending });
  const confirm = () =>
    pending && enable.mutate({ secret: pending.secret, code }, { onSuccess: () => { setPending(null); setCode(""); } });

  return (
    <Section title={t("account.twoStep")}>
      <div className="space-y-3 rounded-slot bg-board p-4">
        <p>{on ? t("account.on") : t("account.off")}</p>
        {on ? (
          <>
            <ActionError error={disable.error} retry={() => disable.mutate()} />
            <Button tone="secondary" busy={disable.isPending} onClick={() => disable.mutate()}>
              {t("account.turnOff")}
            </Button>
          </>
        ) : pending ? (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              confirm();
            }}
          >
            <p className="text-base text-graphite-soft">{t("account.keyHint")}</p>
            <p className="figure rounded-slot bg-plaster p-3 text-figure-sm break-all select-all">{pending.secret}</p>
            <a href={pending.otpauth_uri} className="inline-flex min-h-11 items-center font-bold text-chalk underline decoration-2 underline-offset-4">
              {t("account.openApp")}
            </a>
            <Field
              label={t("account.code")}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              error={enable.error instanceof ApiError && enable.error.status === 401 ? t("login.totpWrong") : undefined}
            />
            <ActionError error={enable.error instanceof ApiError && enable.error.status === 401 ? null : enable.error} retry={confirm} />
            <Button type="submit" busy={enable.isPending} disabled={code.length !== 6}>
              {t("account.confirm")}
            </Button>
          </form>
        ) : (
          <>
            <ActionError error={setup.error} retry={begin} />
            <Button busy={setup.isPending} onClick={begin}>
              {t("account.turnOn")}
            </Button>
          </>
        )}
      </div>
    </Section>
  );
}
