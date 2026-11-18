/**
 * The front door when nobody is logged in: what Mullion does in three lines, "Try it" (a private
 * sample workshop for 24 hours, no account) and "Sign in". The one picture is a window drawn the
 * way the app draws every window.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ApiError } from "../api/client";
import { useStartSandbox } from "../api/workshop";
import { Icon } from "../components/Icon";
import { WindowDrawing } from "../components/WindowDrawing";
import { Button, LanguageToggle, Note, TickLine } from "../components/ui";

export function Landing() {
  const { t, i18n } = useTranslation();
  const sandbox = useStartSandbox();
  const language = i18n.language.startsWith("bs") ? "bs" : "en";
  const failure =
    sandbox.error instanceof ApiError && (sandbox.error.status === 429 || sandbox.error.status === 503)
      ? sandbox.error.message
      : sandbox.error
        ? t("app.offline")
        : null;

  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col px-5 pt-10 pb-10">
      <div className="flex items-center justify-between">
        <p className="text-3xl font-black tracking-tight" style={{ fontStretch: "87.5%" }}>
          {t("app.name")}
        </p>
        <LanguageToggle className="text-chalk" />
      </div>
      <TickLine className="mt-3 w-24" />

      {/* On a phone the actions come before the drawing, so "Try it" is on the first screen. */}
      <div className="mt-8 grid gap-8 sm:mt-10 sm:grid-cols-[1fr_15rem] sm:items-center sm:gap-10">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-extrabold text-balance sm:text-[1.875rem]">{t("landing.tagline")}</h1>
          <ul className="mt-5 space-y-2.5">
            {(["point1", "point2", "point3"] as const).map((point) => (
              <li key={point} className="flex items-start gap-3 text-lg">
                <Icon name="check" className="mt-0.5 size-6 shrink-0 text-chalk" />
                <span>{t(`landing.${point}`)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-8 space-y-3 sm:max-w-sm">
            <Button className="w-full" busy={sandbox.isPending} onClick={() => sandbox.mutate(language)}>
              {t("landing.tryIt")}
            </Button>
            <p className="text-sm text-graphite-soft">{t("landing.tryHint")}</p>
            {failure && <Note>{failure}</Note>}
            <Link
              to="/login"
              className="flex min-h-14 items-center justify-center rounded-slot border-2 border-graphite bg-board px-5 text-lg font-bold transition-colors duration-150 hover:bg-plaster"
            >
              {t("landing.signIn")}
            </Link>
          </div>
        </div>
        <WindowDrawing
          type="two_field_t_mullion"
          width={1400}
          height={1400}
          openings={["tilt_turn_left", "turn_right"]}
          className="mx-auto w-44 sm:w-full"
        />
      </div>

      <p className="mt-auto pt-12 text-sm text-graphite-soft">{t("landing.origin")}</p>
    </main>
  );
}
