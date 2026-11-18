/**
 * The password re-check (step-up) that sensitive changes ask for. It shows where the refused
 * action was, and runs that action again once the password is right.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { needsReauth } from "../api/client";
import { useReauth } from "../api/queries";
import { Button, ErrorNote, Field } from "./ui";

export function Reauth({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const reauth = useReauth();
  const [password, setPassword] = useState("");
  return (
    <form
      className="space-y-3 rounded-slot bg-chalk-tint p-4"
      onSubmit={(e) => {
        e.preventDefault();
        reauth.mutate(password, {
          onSuccess: () => {
            setPassword("");
            onDone();
          },
        });
      }}
    >
      <p className="font-bold">{t("admin.reauthTitle")}</p>
      <p className="text-base text-graphite-soft">{t("admin.reauthHint")}</p>
      <Field
        label={t("login.password")}
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={reauth.isError ? t("login.wrong") : undefined}
      />
      <Button type="submit" busy={reauth.isPending} disabled={!password}>
        {t("admin.reauthSubmit")}
      </Button>
    </form>
  );
}

/**
 * What to show under an action that failed: the re-check when the password is needed again,
 * otherwise the error itself. ``retry`` runs the action again after the re-check.
 */
export function ActionError({ error, retry }: { error: unknown; retry: () => void }) {
  if (!error) return null;
  if (needsReauth(error)) return <Reauth onDone={retry} />;
  return <ErrorNote message={error instanceof Error ? error.message : "error"} />;
}
