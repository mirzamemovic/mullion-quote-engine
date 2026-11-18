/**
 * Joining a workshop from an invite link (``/join#<token>``). The token is after the ``#``, so
 * it never reaches a server log; the page sends it in the request body. The new person picks
 * their own email and password and is logged straight in.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";
import { z } from "zod";

import { ApiError } from "../api/client";
import { useInviteInfo, useJoin } from "../api/workshop";
import { Button, Field, Loading, Note } from "../components/ui";
import { Frame } from "./Login";

const joinSchema = z.object({
  email: z.string().trim().min(3).max(200).regex(/^[^@\s]+@[^@\s]+$/),
  password: z.string().min(12).max(200),
});
type JoinForm = z.infer<typeof joinSchema>;

export function Join() {
  const { t } = useTranslation();
  const location = useLocation();
  const token = location.hash.replace(/^#/, "");
  const info = useInviteInfo(token);
  const join = useJoin();
  const form = useForm<JoinForm>({ resolver: zodResolver(joinSchema), defaultValues: { email: "", password: "" } });

  if (info.isPending && token.length >= 20) return <Loading />;
  if (!info.data) {
    return (
      <Frame title={t("login.title")}>
        <Note>{t("join.invalid")}</Note>
      </Frame>
    );
  }
  const failure = join.error instanceof ApiError ? join.error.message : join.error ? t("app.offline") : null;

  return (
    <Frame title={t("join.title", { workshop: info.data.workshop_name })}>
      <p className="mb-5 text-lg">{t("join.as", { role: t(`roles.${info.data.role}`) })}</p>
      <form
        className="space-y-4"
        noValidate
        onSubmit={(event) => void form.handleSubmit((values) => join.mutate({ token, ...values }))(event)}
      >
        <Field
          label={t("login.email")}
          type="email"
          autoComplete="username"
          inputMode="email"
          {...form.register("email")}
          error={form.formState.errors.email ? t("errors.required") : undefined}
        />
        <Field
          label={t("join.password")}
          type="password"
          autoComplete="new-password"
          hint={t("join.passwordHint")}
          {...form.register("password")}
          error={form.formState.errors.password ? t("join.passwordHint") : undefined}
        />
        {failure && <Note>{failure}</Note>}
        <Button type="submit" className="w-full" busy={join.isPending}>
          {t("join.submit")}
        </Button>
      </form>
    </Frame>
  );
}
