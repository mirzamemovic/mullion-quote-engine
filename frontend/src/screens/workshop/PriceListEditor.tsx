/**
 * One price list. A draft is edited here (amounts, supplier, the estimate flag), filled from the
 * engine's list of missing prices, or replaced from a CSV file; then published from a date. A
 * published list is read-only: it is what quotes were made with.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { ApiError, apiUrl, fileBase64 } from "../../api/client";
import { useMe, useSuppliers } from "../../api/queries";
import type { PriceEntryIn, PriceList } from "../../api/types";
import {
  useDeleteDraft,
  useImportCsv,
  useNewDraft,
  usePriceList,
  usePublishPriceList,
  useSaveEntries,
  useSetupStatus,
} from "../../api/workshop";
import { ActionError } from "../../components/Reauth";
import { Button, Check, ErrorNote, Field, Loading, Note, Section, Select } from "../../components/ui";
import { currencySymbol, day, isoDate, money, moneyInput, parseMoney } from "../../lib/format";
import { unitLabel, workshopLabel } from "../../lib/labels";
import { isOwner, Page } from "./Page";

interface Row {
  key: string;
  item_kind: string;
  item_ref: string;
  colour: PriceEntryIn["colour"];
  unit: PriceEntryIn["unit"];
  supplier_id: string;
  amount: string;
  quoted_on: string;
  is_estimate: boolean;
}

const rowKey = (kind: string, ref: string, colour: string | null | undefined) => `${kind}|${ref}|${colour ?? ""}`;

export function PriceListEditor() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const list = usePriceList(id);
  const [generation, setGeneration] = useState(0);
  if (list.isPending) return <Page title={t("prices.title")} back="/workshop/prices"><Loading /></Page>;
  if (list.isError) return <Page title={t("prices.title")} back="/workshop/prices"><ErrorNote message={list.error.message} /></Page>;
  // After a CSV import (or publishing) the editor starts again from the stored prices; a plain
  // save keeps the rows as typed, which are then the stored ones.
  return <Editor key={`${list.data.id}-${list.data.status}-${generation}`} list={list.data} onImported={() => setGeneration((g) => g + 1)} />;
}

function Editor({ list, onImported }: { list: PriceList; onImported: () => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const owner = isOwner(useMe().data?.role);
  const editable = owner && list.status === "draft";
  const suppliers = useSuppliers();
  const status = useSetupStatus(list.id);
  const save = useSaveEntries(list.id);
  const upload = useImportCsv(list.id);
  const publish = usePublishPriceList(list.id);
  const remove = useDeleteDraft();
  const copy = useNewDraft();
  const navigate = useNavigate();
  const today = isoDate(new Date());
  const [validFrom, setValidFrom] = useState(today);
  const [rows, setRows] = useState<Row[]>(() =>
    list.entries.map((e) => ({
      key: rowKey(e.item_kind, e.item_ref, e.colour),
      item_kind: e.item_kind,
      item_ref: e.item_ref,
      colour: e.colour,
      unit: e.unit,
      supplier_id: e.supplier_id,
      amount: moneyInput(e.amount_cents, lang),
      quoted_on: e.quoted_on,
      is_estimate: e.is_estimate ?? false,
    })),
  );
  const [dirty, setDirty] = useState(false);
  const present = new Set(rows.map((r) => r.key));
  const missing = (status.data?.prices_missing ?? []).filter((p) => !present.has(rowKey(p.kind, p.ref, p.colour)));
  const unpriced = rows.filter((r) => parseMoney(r.amount) === null).length;
  const firstSupplier = suppliers.data?.[0]?.id ?? "";
  const title = list.status === "draft" ? `${t("prices.draft")}: ${list.note || day(list.valid_from, lang)}` : t("admin.validFrom", { date: day(list.valid_from, lang) });

  const change = (key: string, patch: Partial<Row>) => {
    setRows((all) => all.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    setDirty(true);
  };
  const addMissing = () => {
    setRows((all) => [
      ...all,
      ...missing.map((p) => ({
        key: rowKey(p.kind, p.ref, p.colour),
        item_kind: p.kind,
        item_ref: p.ref,
        colour: p.colour as PriceEntryIn["colour"],
        unit: p.unit as PriceEntryIn["unit"],
        supplier_id: firstSupplier,
        amount: "",
        quoted_on: today,
        is_estimate: false,
      })),
    ]);
    setDirty(true);
  };
  const entries = (): PriceEntryIn[] =>
    rows.map((r) => ({
      item_kind: r.item_kind,
      item_ref: r.item_ref,
      colour: r.colour,
      unit: r.unit,
      supplier_id: r.supplier_id,
      amount_cents: parseMoney(r.amount) ?? 0,
      quoted_on: r.quoted_on,
      is_estimate: r.is_estimate,
    }));
  const saveAll = (then?: () => void) => save.mutate(entries(), { onSuccess: () => { setDirty(false); then?.(); } });
  const doPublish = () => (dirty ? saveAll(() => publish.mutate(validFrom)) : publish.mutate(validFrom));
  const sorted = [...rows].sort((a, b) => a.key.localeCompare(b.key));
  const problems = upload.error instanceof ApiError ? upload.error.problems : [];

  return (
    <Page title={title} back="/workshop/prices">
      {!editable && list.status === "published" && <Note tone="hint">{t("prices.readOnly")}</Note>}
      {status.data && status.data.prices_missing.length > 0 && (
        <p className="font-bold">{t("setup.pricesMissing", { count: status.data.prices_missing.length, total: status.data.prices_needed })}</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <a
          href={apiUrl(`/price-lists/${list.id}/csv`)}
          className="flex min-h-14 items-center justify-center rounded-slot border-2 border-graphite bg-board px-5 text-lg font-bold transition-colors duration-150 hover:bg-plaster"
        >
          {t("prices.download")}
        </a>
        {editable && (
          <label className="flex min-h-14 cursor-pointer items-center justify-center rounded-slot border-2 border-graphite bg-board px-5 text-lg font-bold transition-colors duration-150 hover:bg-plaster has-focus-visible:outline-3 has-focus-visible:outline-chalk">
            {t("prices.upload")}
            <input
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) void fileBase64(file).then((data) => upload.mutate(data, { onSuccess: onImported }));
              }}
            />
          </label>
        )}
        {owner && list.status === "published" && (
          <Button tone="secondary" busy={copy.isPending} onClick={() => copy.mutate({ copy_from: list.id }, { onSuccess: (l) => void navigate(`/workshop/prices/${l.id}`) })}>
            {t("prices.newDraft")}
          </Button>
        )}
      </div>
      {editable && <p className="text-sm text-graphite-soft">{t("prices.uploadHint")}</p>}
      {problems.length > 0 && (
        <Note>
          <p>{t("prices.problems", { count: problems.length })}</p>
          <ul className="mt-2 space-y-1 font-normal">
            {problems.slice(0, 20).map((p) => (
              <li key={`${p.row}-${p.column}-${p.message}`}>{t("prices.problem", { row: p.row, column: p.column, message: p.message })}</li>
            ))}
          </ul>
        </Note>
      )}
      {upload.isError && problems.length === 0 && <ErrorNote message={upload.error.message} />}

      {editable && missing.length > 0 && (
        <Button tone="secondary" className="w-full" onClick={addMissing}>
          {t("prices.addMissing", { count: missing.length })}
        </Button>
      )}

      <Section title={t("prices.entries", { count: rows.length })}>
        <ul className="space-y-2">
          {sorted.map((r) => {
            const amountError = editable && r.amount !== "" && parseMoney(r.amount) === null;
            return (
              <li key={r.key} className="rounded-slot bg-board p-3">
                <div className="flex items-start justify-between gap-3">
                  <span className="min-w-0">
                    <span className="block font-semibold">
                      {workshopLabel(`${r.item_kind} ${r.item_ref}`, lang)}
                      {r.colour ? ` · ${t(`colours.${r.colour}`)}` : ""}
                    </span>
                    <span className="block text-sm text-graphite-soft">{t("prices.per", { unit: unitLabel(r.unit, lang) })}</span>
                  </span>
                  {editable ? (
                    <Field
                      label={t("prices.amount", { currency: currencySymbol() })}
                      inputMode="decimal"
                      value={r.amount}
                      onChange={(e) => change(r.key, { amount: e.target.value.replace(/[^\d,.]/g, "") })}
                      error={amountError ? t("errors.number") : undefined}
                      className="w-36 shrink-0"
                    />
                  ) : (
                    <span className="figure shrink-0 text-figure-sm">{money(parseMoney(r.amount) ?? 0, lang)}</span>
                  )}
                </div>
                {editable && (
                  <div className="mt-2 grid items-end gap-2 sm:grid-cols-[1fr_auto]">
                    <Select
                      label={t("prices.pickSupplier")}
                      value={r.supplier_id}
                      onChange={(v) => change(r.key, { supplier_id: v })}
                      options={(suppliers.data ?? []).map((s) => ({ value: s.id, label: s.name }))}
                    />
                    <Check label={t("prices.estimate")} checked={r.is_estimate} onChange={(v) => change(r.key, { is_estimate: v })} />
                  </div>
                )}
                {!editable && r.is_estimate && <span className="mt-1 block text-sm font-bold text-crayon">{t("prices.estimate")}</span>}
              </li>
            );
          })}
        </ul>
      </Section>

      {editable && (
        <div className="space-y-3">
          {unpriced > 0 && <Note>{t("prices.needAmounts", { count: unpriced })}</Note>}
          {save.isError && <ErrorNote message={save.error.message} />}
          <Button tone="secondary" className="w-full" busy={save.isPending} disabled={!dirty || unpriced > 0} onClick={() => saveAll()}>
            {t("prices.save")}
          </Button>
          <Field label={t("prices.validFrom")} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
          <ActionError error={publish.error} retry={doPublish} />
          <Button className="w-full" busy={publish.isPending} disabled={unpriced > 0 || rows.length === 0} onClick={doPublish}>
            {t("prices.publish")}
          </Button>
          <Button tone="danger" className="w-full" busy={remove.isPending} onClick={() => remove.mutate(list.id, { onSuccess: () => void navigate("/workshop/prices") })}>
            {t("prices.deleteDraft")}
          </Button>
        </div>
      )}
    </Page>
  );
}
