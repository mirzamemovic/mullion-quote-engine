/** Log in once and stay logged in. The admin then gives the 6-digit code from the phone. */
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { ApiError } from "../api/client";
import { useLogin, useLogout, useTotp } from "../api/queries";
import { Button, Field, LanguageToggle, TickLine } from "../components/ui";

const loginSchema = z.object({
  email: z.string().trim().min(3).max(200),
  password: z.string().min(1).max(200),
});
type LoginForm = z.infer<typeof loginSchema>;

function Frame({ title, children }: { title: string; children: React.ReactNode }) {
  const { t } = useTranslation();
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pt-10 pb-8">
      <div className="flex items-center justify-between">
        <p className="text-3xl font-black tracking-tight" style={{ fontStretch: "87.5%" }}>
          {t("app.name")}
        </p>
        <LanguageToggle className="text-chalk" />
      </div>
      {/* The dimension string under the name: the app's one mark. */}
      <TickLine className="mt-3 w-24" />
      <h1 className="mt-10 text-2xl font-extrabold">{title}</h1>
      <div className="mt-5">{children}</div>
    </main>
  );
}

export function Login() {
  const { t } = useTranslation();
  const login = useLogin();
  const form = useForm<LoginForm>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });
  const failure =
    login.error instanceof ApiError
      ? login.error.status === 429
        ? t("login.locked")
        : login.error.status === 401
          ? t("login.wrong")
          : login.error.message
      : login.error
        ? t("app.offline")
        : null;

  return (
    <Frame title={t("login.title")}>
      <form
        className="space-y-4"
        onSubmit={(event) => void form.handleSubmit((values) => login.mutate(values))(event)}
        noValidate
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
          label={t("login.password")}
          type="password"
          autoComplete="current-password"
          {...form.register("password")}
          error={form.formState.errors.password ? t("errors.required") : undefined}
        />
        {failure && (
          <p role="alert" className="rounded-slot bg-crayon-tint p-3 font-semibold">
            {failure}
          </p>
        )}
        <Button type="submit" className="w-full" busy={login.isPending}>
          {t("login.submit")}
        </Button>
      </form>
    </Frame>
  );
}

export function Totp() {
  const { t } = useTranslation();
  const totp = useTotp();
  const logout = useLogout();
  const form = useForm<{ code: string }>({ defaultValues: { code: "" } });
  const failure =
    totp.error instanceof ApiError && totp.error.status === 429
      ? t("login.locked")
      : totp.error
        ? t("login.totpWrong")
        : null;
  return (
    <Frame title={t("login.totpTitle")}>
      <form
        className="space-y-4"
        onSubmit={(event) => void form.handleSubmit(({ code }) => totp.mutate(code.trim()))(event)}
      >
        <Field
          label={t("login.totpTitle")}
          hint={t("login.totpHint")}
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          pattern="\d{6}"
          className="figure"
          {...form.register("code", { required: true, pattern: /^\d{6}$/ })}
        />
        {failure && (
          <p role="alert" className="rounded-slot bg-crayon-tint p-3 font-semibold">
            {failure}
          </p>
        )}
        <Button type="submit" className="w-full" busy={totp.isPending}>
          {t("login.totpSubmit")}
        </Button>
        <Button tone="quiet" className="w-full" onClick={() => logout.mutate()}>
          {t("app.logout")}
        </Button>
      </form>
    </Frame>
  );
}
