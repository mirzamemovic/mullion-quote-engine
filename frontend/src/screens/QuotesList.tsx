/** The quotes list: newest first, search, a status filter, and one big button for a new quote. */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useMe, useQuotes } from "../api/queries";
import { useSetupStatus } from "../api/workshop";
import type { QuoteStatus } from "../api/types";
import { Icon } from "../components/Icon";
import { ErrorNote, LanguageToggle, Loading, TopBar } from "../components/ui";
import { money } from "../lib/format";
import { StatusPill } from "./StatusPill";

const FILTERS = ["", "draft", "sent", "accepted", "expired", "rejected"] as const;

export function QuotesList() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const me = useMe();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string>("");
  const quotes = useQuotes(search.trim(), status);
  const setup = useSetupStatus();

  return (
    <>
      <TopBar
        title={t("quotes.title")}
        subtitle={me.data?.workshop_name}
        actions={
          <div className="flex items-center gap-1">
            <LanguageToggle className="text-white" />
            <Link to="/workshop" aria-label={t("app.workshop")} title={t("app.workshop")} className="grid size-11 place-items-center rounded-slot hover:bg-shell-raised">
              <Icon name="sliders" />
            </Link>
          </div>
        }
      />
      <main className="mx-auto max-w-3xl px-4 pb-32">
        {me.data?.role === "owner" && setup.data && !setup.data.ready && (
          <Link to="/workshop/setup" className="mt-4 flex min-h-12 items-center gap-2 rounded-slot bg-chalk-tint px-4 py-3 font-semibold hover:bg-chalk-tint/70">
            <Icon name="sliders" className="size-5 shrink-0 text-chalk-deep" />
            <span className="flex-1">{t("quotes.setup", { percent: setup.data.percent })}</span>
            <Icon name="forward" className="size-5 shrink-0 text-chalk-deep" />
          </Link>
        )}
        <div className="sticky top-16 z-10 -mx-4 bg-plaster px-4 pt-4 pb-3">
          <label className="relative block">
            <span className="sr-only">{t("quotes.search")}</span>
            <Icon name="search" className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-graphite-soft" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("quotes.search")}
              className="h-14 w-full rounded-slot border-2 border-graphite-line bg-board pr-4 pl-12 text-lg outline-none focus:border-chalk"
            />
          </label>
          <div className="mt-3 -mx-4 flex gap-2 overflow-x-auto px-4 pb-1" role="group" aria-label={t("quotes.all")}>
            {FILTERS.map((value) => (
              <button
                key={value || "all"}
                type="button"
                aria-pressed={status === value}
                onClick={() => setStatus(value)}
                className={`min-h-11 shrink-0 rounded-full px-4 text-base font-bold transition-colors duration-150 ${status === value ? "bg-graphite text-white" : "bg-board text-graphite hover:bg-plaster-deep"}`}
              >
                {value ? t(`status.${value}`) : t("quotes.all")}
              </button>
            ))}
          </div>
        </div>

        {quotes.isPending && <Loading />}
        {quotes.isError && <ErrorNote message={quotes.error.message} onRetry={() => void quotes.refetch()} />}
        {quotes.data && quotes.data.length === 0 && (
          <p className="py-12 text-center text-lg text-graphite-soft">
            {search || status ? t("quotes.emptyFiltered") : t("quotes.empty")}
          </p>
        )}
        <ul className="space-y-2">
          {quotes.data?.map((q) => (
            <li key={q.id}>
              <Link
                to={`/quotes/${q.id}`}
                className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 rounded-slot bg-board p-4 hover:bg-chalk-tint/50"
              >
                <span className="min-w-0 truncate text-lg font-bold">{q.client_name}</span>
                {q.total_cents != null ? (
                  <span className="figure text-right text-figure-md">{money(q.total_cents, lang)}</span>
                ) : (
                  <span className="text-right text-sm font-semibold text-graphite-soft">{t("quotes.noTotal")}</span>
                )}
                <span className="figure text-figure-sm text-graphite-soft">{q.number}</span>
                <span className="justify-self-end">
                  <StatusPill status={q.status as QuoteStatus} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </main>
      <div className="fixed inset-x-0 bottom-0 z-20 mx-auto max-w-3xl bg-plaster/95 px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Link
          to="/quotes/new"
          className="flex min-h-16 w-full items-center justify-center gap-2 rounded-slot bg-chalk text-xl font-extrabold text-white shadow-lift hover:bg-chalk-deep"
        >
          <Icon name="plus" />
          {t("quotes.new")}
        </Link>
      </div>
    </>
  );
}
