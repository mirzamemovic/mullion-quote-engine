/** A new quote: pick the client (or add one), the profile system, and go straight to measuring. */
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { z } from "zod";

import { useClients, useCreateClient, useCreateQuote, useSystems } from "../api/queries";
import type { Client, ProfileSystem } from "../api/types";
import { Icon } from "../components/Icon";
import { Button, ErrorNote, Field, TopBar } from "../components/ui";
import { lastChoices, remember } from "../lib/remember";

const clientSchema = z.object({
  name: z.string().trim().min(1).max(200),
  phone: z.string().trim().max(50),
  place: z.string().trim().max(200),
});
type ClientForm = z.infer<typeof clientSchema>;

/** Profile systems grouped by material; each card names the brand, series and depth. */
function SystemPicker({
  systems,
  value,
  onChange,
}: {
  systems: ProfileSystem[];
  value: string;
  onChange: (id: string) => void;
}) {
  const { t } = useTranslation();
  const groups = (["pvc", "aluminium"] as const)
    .map((material) => ({ material, items: systems.filter((s) => s.material === material) }))
    .filter((group) => group.items.length > 0);
  return (
    <section aria-labelledby="system" className="space-y-4">
      <h2 id="system" className="text-2xl font-extrabold">
        {t("newQuote.system")}
      </h2>
      {groups.map(({ material, items }) => (
        <fieldset key={material}>
          <legend className="mb-2 text-base font-bold text-graphite-soft">
            {t(`newQuote.${material}`)}
          </legend>
          <div className="grid gap-2 sm:grid-cols-3">
            {items.map((s) => {
              const chosen = s.id === value;
              return (
                <label
                  key={s.id}
                  className={`flex min-h-16 cursor-pointer flex-col justify-center rounded-slot px-4 py-2 transition-colors duration-150 has-focus-visible:outline-3 has-focus-visible:outline-chalk ${chosen ? "bg-chalk-tint outline-3 outline-chalk" : "bg-board hover:bg-chalk-tint/50"}`}
                >
                  <input
                    type="radio"
                    name="profile-system"
                    className="sr-only"
                    value={s.id}
                    checked={chosen}
                    onChange={() => onChange(s.id)}
                  />
                  <span className="text-lg leading-tight font-bold">{s.brand}</span>
                  <span className="text-sm leading-snug text-graphite-soft">
                    {s.series} · <span className="figure">{s.depth_mm}</span> mm
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}
    </section>
  );
}

export function NewQuote() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [client, setClient] = useState<Client | null>(null);
  const [adding, setAdding] = useState(false);
  const clients = useClients(search.trim());
  const systems = useSystems();
  const createClient = useCreateClient();
  const createQuote = useCreateQuote();
  const enabled = (systems.data ?? []).filter((s) => s.enabled);
  const [systemId, setSystemId] = useState<string>(lastChoices().systemId ?? "");
  const chosenSystem = enabled.find((s) => s.id === systemId) ?? enabled[0];
  const form = useForm<ClientForm>({
    resolver: zodResolver(clientSchema),
    defaultValues: { name: "", phone: "", place: "" },
  });

  function start(forClient: Client) {
    if (!chosenSystem) return;
    remember({ systemId: chosenSystem.id });
    createQuote.mutate(
      { client_id: forClient.id, profile_system_id: chosenSystem.id },
      { onSuccess: (quote) => void navigate(`/quotes/${quote.id}/positions/new`, { replace: true }) },
    );
  }

  return (
    <>
      <TopBar title={t("newQuote.title")} back="/" />
      <main className="mx-auto max-w-3xl space-y-6 px-4 pt-5 pb-10">
        {systems.isError && <ErrorNote message={systems.error.message} />}
        {systems.data && enabled.length === 0 && <ErrorNote message={t("newQuote.noSystem")} />}
        {enabled.length > 1 && chosenSystem && (
          <SystemPicker systems={enabled} value={chosenSystem.id} onChange={setSystemId} />
        )}

        <section aria-labelledby="client">
          <h2 id="client" className="text-2xl font-extrabold">
            {t("newQuote.client")}
          </h2>
          {!adding && (
            <>
              <label className="relative mt-3 block">
                <span className="sr-only">{t("newQuote.search")}</span>
                <Icon name="search" className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-graphite-soft" />
                <input
                  type="search"
                  value={search}
                  autoFocus
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setClient(null);
                  }}
                  placeholder={t("newQuote.search")}
                  className="h-14 w-full rounded-slot border-2 border-graphite-line bg-board pr-4 pl-12 text-lg outline-none focus:border-chalk"
                />
              </label>
              <ul className="mt-3 space-y-2">
                {(clients.data ?? []).slice(0, 8).map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      aria-pressed={client?.id === c.id}
                      onClick={() => setClient(c)}
                      className={`flex min-h-14 w-full items-center justify-between gap-3 rounded-slot px-4 text-left ${client?.id === c.id ? "bg-chalk-tint outline-3 outline-chalk" : "bg-board hover:bg-chalk-tint/50"}`}
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-lg font-bold">{c.name}</span>
                        {(c.place || c.phone) && (
                          <span className="block truncate text-sm text-graphite-soft">
                            {[c.place, c.phone].filter(Boolean).join(" · ")}
                          </span>
                        )}
                      </span>
                      {client?.id === c.id && <Icon name="check" className="text-chalk" />}
                    </button>
                  </li>
                ))}
              </ul>
              <Button tone="secondary" icon="plus" className="mt-3 w-full" onClick={() => setAdding(true)}>
                {t("newQuote.addClient")}
              </Button>
            </>
          )}

          {adding && (
            <form
              className="mt-3 space-y-4"
              onSubmit={(event) =>
                void form.handleSubmit((values) =>
                  createClient.mutate(values, { onSuccess: (created) => start(created) }),
                )(event)
              }
            >
              <Field
                label={t("newQuote.name")}
                autoComplete="off"
                autoFocus
                {...form.register("name")}
                error={form.formState.errors.name ? t("errors.required") : undefined}
              />
              <Field label={t("newQuote.phone")} type="tel" inputMode="tel" autoComplete="off" {...form.register("phone")} />
              <Field label={t("newQuote.place")} autoComplete="off" {...form.register("place")} />
              {(createClient.isError || createQuote.isError) && (
                <ErrorNote message={(createClient.error ?? createQuote.error)?.message ?? ""} />
              )}
              <div className="grid grid-cols-[auto_1fr] gap-2">
                <Button tone="secondary" onClick={() => setAdding(false)}>
                  {t("app.cancel")}
                </Button>
                <Button type="submit" icon="forward" busy={createClient.isPending || createQuote.isPending} disabled={!chosenSystem}>
                  {t("newQuote.create")}
                </Button>
              </div>
            </form>
          )}
        </section>

        {!adding && (
          <>
            {createQuote.isError && <ErrorNote message={createQuote.error.message} />}
            <Button className="w-full" icon="forward" disabled={!client || !chosenSystem} busy={createQuote.isPending} onClick={() => client && start(client)}>
              {t("newQuote.create")}
            </Button>
          </>
        )}
      </main>
    </>
  );
}
