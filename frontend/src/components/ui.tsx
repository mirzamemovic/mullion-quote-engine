/** The app's controls: standard buttons, fields and bars in the site-wall palette. */
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { setLanguage } from "../i18n";
import { Icon, type IconName } from "./Icon";

type Tone = "primary" | "secondary" | "quiet" | "danger";

const TONES: Record<Tone, string> = {
  primary:
    "bg-chalk text-white hover:bg-chalk-deep active:bg-chalk-deep disabled:bg-graphite-line",
  secondary:
    "bg-board text-graphite border-2 border-graphite hover:bg-plaster active:bg-plaster-deep disabled:border-graphite-line disabled:text-graphite-soft",
  quiet: "bg-transparent text-chalk hover:bg-chalk-tint active:bg-chalk-tint",
  danger: "bg-board text-crayon border-2 border-crayon hover:bg-crayon-tint",
};

export function Button({
  tone = "primary",
  icon,
  busy = false,
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: Tone;
  icon?: IconName;
  busy?: boolean;
}) {
  return (
    <button
      type="button"
      {...rest}
      disabled={rest.disabled || busy}
      aria-busy={busy || undefined}
      className={`inline-flex min-h-14 items-center justify-center gap-2 rounded-slot px-5 text-lg font-bold transition-colors duration-150 ${TONES[tone]} ${className}`}
    >
      {icon && <Icon name={icon} />}
      <span>{children}</span>
    </button>
  );
}

export function IconButton({
  icon,
  label,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: IconName; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...rest}
      className={`grid size-11 place-items-center rounded-slot transition-colors duration-150 ${className}`}
    >
      <Icon name={icon} />
    </button>
  );
}

export function Field({
  label,
  error,
  hint,
  className = "",
  ...input
}: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string }) {
  const id = useId();
  const described = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-base font-bold">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={described}
        {...input}
        className={`h-14 w-full rounded-slot border-2 bg-board px-4 text-lg outline-none transition-colors duration-150 focus:border-chalk ${error ? "border-crayon" : "border-graphite-line"}`}
      />
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1.5 text-sm text-graphite-soft">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-sm font-semibold text-crayon">
          {error}
        </p>
      )}
    </div>
  );
}

export function TopBar({
  title,
  subtitle,
  back,
  actions,
}: {
  title: string;
  subtitle?: string;
  back?: string;
  actions?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <header className="sticky top-0 z-20 bg-shell text-white">
      <div className="mx-auto flex min-h-16 max-w-3xl items-center gap-3 px-3">
        {back !== undefined && (
          <Link
            to={back}
            aria-label={t("app.back")}
            className="grid size-11 shrink-0 place-items-center rounded-slot bg-shell-raised hover:bg-graphite-soft"
          >
            <Icon name="back" />
          </Link>
        )}
        <div className="min-w-0 flex-1 py-2">
          <h1 className="truncate text-lg leading-tight font-extrabold">{title}</h1>
          {subtitle && <p className="line-clamp-2 text-sm text-white/75">{subtitle}</p>}
        </div>
        {actions}
      </div>
    </header>
  );
}

export function LanguageToggle({ className = "" }: { className?: string }) {
  const { t, i18n } = useTranslation();
  const next = i18n.language.startsWith("en") ? "bs" : "en";
  return (
    <button
      type="button"
      onClick={() => setLanguage(next)}
      lang={next}
      className={`min-h-11 rounded-slot px-3 text-sm font-bold underline decoration-2 underline-offset-4 ${className}`}
    >
      {t("app.language")}
    </button>
  );
}

export function DemoBanner() {
  const { t } = useTranslation();
  return (
    <p
      role="note"
      className="flex items-center justify-center gap-2 bg-plaster-deep px-4 py-1.5 text-center text-sm font-extrabold tracking-wide text-graphite"
    >
      <span
        aria-hidden="true"
        className="h-3.5 w-6 rounded-[2px] bg-[repeating-linear-gradient(135deg,var(--color-graphite)_0_2px,transparent_2px_5px)]"
      />
      {t("app.demo")}
    </p>
  );
}

/** The pencil tick line under a size: a rule with an end tick on each side. */
export function TickLine({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`relative block h-0 border-t-2 border-chalk before:absolute before:-top-[7px] before:left-0 before:h-3 before:w-0.5 before:bg-chalk after:absolute after:-top-[7px] after:right-0 after:h-3 after:w-0.5 after:bg-chalk ${className}`}
    />
  );
}

/** A size written like a dimension string: the number on top, the ticked line under it. */
export function SizeMark({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex flex-col items-stretch ${className}`}>
      <span className="figure px-1">{children}</span>
      <TickLine className="mt-1 mb-1" />
    </span>
  );
}

export function Loading() {
  const { t } = useTranslation();
  return (
    <p role="status" className="px-4 py-10 text-center text-lg text-graphite-soft">
      {t("app.loading")}
    </p>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div role="alert" className="mx-4 my-4 rounded-slot bg-crayon-tint p-4 text-graphite">
      <p className="flex items-start gap-2 font-semibold">
        <Icon name="alert" className="mt-0.5 size-5 shrink-0 text-crayon" />
        <span>{message}</span>
      </p>
      {onRetry && (
        <Button tone="secondary" className="mt-3 min-h-12" onClick={onRetry}>
          {t("app.retry")}
        </Button>
      )}
    </div>
  );
}

/** A segmented choice: big targets, one tap, the chosen one in chalk blue. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  hideLabel = false,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  hideLabel?: boolean;
}) {
  return (
    <fieldset>
      <legend className={hideLabel ? "sr-only" : "mb-1.5 text-base font-bold"}>{label}</legend>
      <div className="flex gap-1 rounded-slot bg-plaster-deep p-1">
        {options.map((option) => (
          <label
            key={option.value}
            className={`flex min-h-11 flex-auto cursor-pointer items-center justify-center rounded-[0.5rem] px-3 text-center text-[0.9375rem] leading-tight font-bold whitespace-nowrap transition-colors duration-150 has-focus-visible:outline-3 has-focus-visible:outline-chalk ${value === option.value ? "bg-chalk text-white shadow-lift" : "text-graphite hover:bg-board/60"}`}
          >
            <input
              type="radio"
              className="sr-only"
              name={label}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
