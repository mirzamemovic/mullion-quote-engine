/**
 * The team: who can log in and in which role, invite links for new people (copied or shared,
 * since there is no email), and the devices that are logged in. Changing someone's login asks for
 * the password again.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useMe } from "../../api/queries";
import type { InviteCreated, Role } from "../../api/types";
import { useChangeUser, useCreateInvite, useInvites, useRevokeInvite, useRevokeSession, useSessions, useUsers } from "../../api/workshop";
import { ActionError } from "../../components/Reauth";
import { Button, ErrorNote, Loading, Note, Section, Segmented } from "../../components/ui";
import { day } from "../../lib/format";
import { Page } from "./Page";

export function Team() {
  const { t } = useTranslation();
  const me = useMe().data;
  return (
    <Page title={t("team.title")}>
      <People myId={me?.user_id ?? ""} />
      {me?.sandbox_expires_at ? <Note tone="hint">{t("team.sandbox")}</Note> : <Invites />}
      <Devices />
    </Page>
  );
}

function People({ myId }: { myId: string }) {
  const { t } = useTranslation();
  const users = useUsers();
  const change = useChangeUser();
  const [last, setLast] = useState<{ id: string; body: { is_active?: boolean; role?: Role } } | null>(null);
  const run = (id: string, body: { is_active?: boolean; role?: Role }) => {
    setLast({ id, body });
    change.mutate({ id, body });
  };

  return (
    <Section title={t("team.people")}>
      {users.isPending && <Loading />}
      {users.isError && <ErrorNote message={users.error.message} />}
      <ul className="space-y-2">
        {users.data?.map((u) => (
          <li key={u.id} className="rounded-slot bg-board p-3">
            <p className="font-bold break-all">
              {u.email}
              {u.id === myId && <span className="font-normal text-graphite-soft"> ({t("team.you")})</span>}
            </p>
            <p className="text-sm text-graphite-soft">
              {t(`roles.${u.role}`)}
              {!u.is_active && ` · ${t("team.off")}`}
            </p>
            {u.id !== myId && (
              <div className="mt-2 flex flex-wrap gap-2">
                <Button tone="secondary" className="min-h-12" onClick={() => run(u.id, { role: u.role === "owner" ? "staff" : "owner" })}>
                  {u.role === "owner" ? t("team.makeStaff") : t("team.makeOwner")}
                </Button>
                <Button tone={u.is_active ? "danger" : "secondary"} className="min-h-12" onClick={() => run(u.id, { is_active: !u.is_active })}>
                  {u.is_active ? t("team.turnOff") : t("team.turnOn")}
                </Button>
              </div>
            )}
          </li>
        ))}
      </ul>
      <ActionError error={change.error} retry={() => last && change.mutate(last)} />
    </Section>
  );
}

function Invites() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const invites = useInvites();
  const create = useCreateInvite();
  const revoke = useRevokeInvite();
  const [role, setRole] = useState<Role>("staff");
  const [made, setMade] = useState<InviteCreated | null>(null);
  const [copied, setCopied] = useState(false);
  // The token goes after "#": browsers never send that part, so it stays out of every log.
  const link = made ? `${window.location.origin}/join#${made.token}` : "";

  return (
    <Section title={t("team.invite")}>
      <div className="space-y-3 rounded-slot bg-board p-4">
        <Segmented label={t("team.inviteAs")} value={role} onChange={setRole} options={[{ value: "staff", label: t("roles.staff") }, { value: "owner", label: t("roles.owner") }]} />
        <Button className="w-full" busy={create.isPending} onClick={() => create.mutate(role, { onSuccess: (inv) => { setMade(inv); setCopied(false); } })}>
          {t("team.inviteCreate")}
        </Button>
        {create.isError && <ErrorNote message={create.error.message} />}
        {made && (
          <div className="space-y-2 rounded-slot bg-chalk-tint p-3">
            <p className="font-semibold">{t("team.inviteLink")}</p>
            <p className="text-sm break-all select-all">{link}</p>
            <div className="flex flex-wrap gap-2">
              <Button
                tone="secondary"
                icon="copy"
                className="min-h-12"
                onClick={() => void navigator.clipboard?.writeText(link).then(() => setCopied(true))}
              >
                {t("app.copy")}
              </Button>
              {typeof navigator.share === "function" && (
                <Button tone="secondary" icon="share" className="min-h-12" onClick={() => void navigator.share({ url: link }).catch(() => undefined)}>
                  {t("summary.share")}
                </Button>
              )}
            </div>
            {copied && <p role="status" className="text-sm font-semibold text-tick">{t("app.copied")}</p>}
          </div>
        )}
      </div>
      {(invites.data?.length ?? 0) > 0 && (
        <>
          <h3 className="text-lg font-extrabold">{t("team.pending")}</h3>
          <ul className="space-y-2">
            {invites.data?.map((inv) => (
              <li key={inv.id} className="flex items-center justify-between gap-3 rounded-slot bg-board px-4 py-3">
                <span>
                  {t(`roles.${inv.role}`)} · {t("team.until", { date: day(inv.expires_at, lang) })}
                </span>
                <Button tone="quiet" className="min-h-11" onClick={() => revoke.mutate(inv.id)}>
                  {t("team.cancel")}
                </Button>
              </li>
            ))}
          </ul>
        </>
      )}
    </Section>
  );
}

function Devices() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const sessions = useSessions();
  const revoke = useRevokeSession();
  return (
    <Section title={t("team.sessions")}>
      <ul className="space-y-2">
        {sessions.data?.map((s) => (
          <li key={s.id} className="flex items-center justify-between gap-3 rounded-slot bg-board px-4 py-3">
            <span className="min-w-0">
              <span className="block truncate">{s.user_agent || "—"}</span>
              <span className="block text-sm text-graphite-soft">{t("team.lastSeen", { date: day(s.last_seen_at, lang) })}</span>
            </span>
            <Button tone="quiet" className="min-h-11 shrink-0" onClick={() => revoke.mutate(s.id)}>
              {t("team.logOut")}
            </Button>
          </li>
        ))}
      </ul>
      {revoke.isError && <ErrorNote message={revoke.error.message} />}
    </Section>
  );
}
