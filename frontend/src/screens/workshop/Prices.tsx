/**
 * Prices and suppliers at the workshop PC: every price list (the one in use, older ones and
 * drafts), a supplier's price change as a new version, and the supplier list. A published list
 * never changes; changes go through a draft.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useBump, useMe, usePriceLists, useSuppliers } from "../../api/queries";
import type { Supplier } from "../../api/types";
import { useAddSupplier, useNewDraft } from "../../api/workshop";
import { ActionError } from "../../components/Reauth";
import { Button, ErrorNote, Field, LinkRow, Loading, Section, Select } from "../../components/ui";
import { day, isoDate } from "../../lib/format";
import { isOwner, Page } from "./Page";

const KINDS: Supplier["kind"][] = ["profile", "glass", "hardware", "other"];

export function Prices() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const owner = isOwner(useMe().data?.role);
  const lists = usePriceLists();
  const draft = useNewDraft();
  const navigate = useNavigate();
  const today = isoDate(new Date());
  const inUse = lists.data?.find((l) => l.status === "published" && l.valid_from <= today);
  const open = (id: string) => void navigate(`/workshop/prices/${id}`);

  return (
    <Page title={t("prices.title")}>
      <Section title={t("prices.lists")}>
        {lists.isPending && <Loading />}
        {lists.isError && <ErrorNote message={lists.error.message} />}
        <div className="space-y-3">
          {lists.data?.map((list) => (
            <LinkRow
              key={list.id}
              to={`/workshop/prices/${list.id}`}
              title={list.status === "draft" ? `${t("prices.draft")}: ${list.note || day(list.valid_from, lang)}` : list.id === inUse?.id ? t("prices.inUse", { date: day(list.valid_from, lang) }) : t("admin.validFrom", { date: day(list.valid_from, lang) })}
              status={`${t("prices.entries", { count: list.entries.length })}${list.status === "published" && list.note ? ` · ${list.note}` : ""}`}
              done={list.id === inUse?.id ? true : undefined}
            />
          ))}
        </div>
        {owner && (
          <div className="grid gap-3 sm:grid-cols-2">
            {inUse && (
              <Button tone="secondary" busy={draft.isPending} onClick={() => draft.mutate({ copy_from: inUse.id }, { onSuccess: (l) => open(l.id) })}>
                {t("prices.newDraft")}
              </Button>
            )}
            <Button tone="secondary" busy={draft.isPending} onClick={() => draft.mutate({}, { onSuccess: (l) => open(l.id) })}>
              {t("prices.emptyDraft")}
            </Button>
          </div>
        )}
        {draft.isError && <ErrorNote message={draft.error.message} />}
      </Section>
      {owner && inUse && <SupplierBump listId={inUse.id} />}
      <Suppliers owner={owner} />
    </Page>
  );
}

function SupplierBump({ listId }: { listId: string }) {
  const { t } = useTranslation();
  const suppliers = useSuppliers();
  const bump = useBump();
  const [supplierId, setSupplierId] = useState("");
  const [percent, setPercent] = useState("");
  const [validFrom, setValidFrom] = useState(isoDate(new Date()));
  // "+4,5" -> 450 basis points, read as text (no float rounding).
  const match = /^([+-]?)(\d{1,3})(?:[.,](\d{1,2}))?$/.exec(percent.trim());
  const bp = match ? (match[1] === "-" ? -1 : 1) * (Number(match[2]) * 100 + Number((match[3] ?? "").padEnd(2, "0"))) : 0;
  const ready = supplierId && bp !== 0;
  const submit = () =>
    bump.mutate({ listId, body: { supplier_id: supplierId, bp, valid_from: validFrom } }, { onSuccess: () => setPercent("") });

  return (
    <Section title={t("admin.bump")}>
      <form
        className="space-y-3 rounded-slot bg-board p-4"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Select
          label={t("admin.bumpSupplier")}
          value={supplierId}
          onChange={setSupplierId}
          options={[{ value: "", label: "–" }, ...(suppliers.data ?? []).map((s) => ({ value: s.id, label: s.name }))]}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("admin.bumpPercent")} inputMode="decimal" value={percent} onChange={(e) => setPercent(e.target.value.replace(/[^\d,.+-]/g, ""))} />
          <Field label={t("admin.bumpDate")} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
        </div>
        <ActionError error={bump.error} retry={submit} />
        <Button type="submit" busy={bump.isPending} disabled={!ready}>
          {t("admin.bumpSubmit")}
        </Button>
        {bump.isSuccess && <p role="status" className="font-semibold text-tick">{t("admin.saved")}</p>}
      </form>
    </Section>
  );
}

function Suppliers({ owner }: { owner: boolean }) {
  const { t } = useTranslation();
  const suppliers = useSuppliers();
  const add = useAddSupplier();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [kind, setKind] = useState<Supplier["kind"]>("profile");

  return (
    <Section title={t("prices.suppliers")}>
      <ul className="space-y-2">
        {suppliers.data?.length === 0 && <li className="text-graphite-soft">{t("systems.none")}</li>}
        {suppliers.data?.map((s) => (
          <li key={s.id} className="rounded-slot bg-board px-4 py-3">
            <span className="block font-bold">{s.name}</span>
            <span className="block text-sm text-graphite-soft">
              {t(`prices.kinds.${s.kind}`)}
              {s.phone ? ` · ${s.phone}` : ""}
            </span>
          </li>
        ))}
      </ul>
      {owner && (
        <form
          className="grid grid-cols-2 gap-3 rounded-slot bg-board p-4"
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate({ name, phone, kind }, { onSuccess: () => { setName(""); setPhone(""); } });
          }}
        >
          <h3 className="col-span-2 text-lg font-extrabold">{t("prices.addSupplier")}</h3>
          <Field className="col-span-2" label={t("prices.supplierName")} value={name} onChange={(e) => setName(e.target.value)} />
          <Field label={t("prices.supplierPhone")} inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value.slice(0, 50))} />
          <Select label={t("prices.supplierKind")} value={kind} onChange={(v) => setKind(v as Supplier["kind"])} options={KINDS.map((k) => ({ value: k, label: t(`prices.kinds.${k}`) }))} />
          {add.isError && <div className="col-span-2"><ErrorNote message={add.error.message} /></div>}
          <Button type="submit" className="col-span-2" busy={add.isPending} disabled={!name.trim()}>
            {t("prices.addSupplier")}
          </Button>
        </form>
      )}
    </Section>
  );
}
