/** Add or edit one window: measure, pick the type, set the details, save into the draft. */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams, useSearchParams } from "react-router";

import { usePriceLists, useQuote, useSaveRevision } from "../../api/queries";
import type { Colour, PositionIn, PositionOut, QuoteDetail } from "../../api/types";
import { ErrorNote, Loading, TopBar } from "../../components/ui";
import { lastChoices, remember } from "../../lib/remember";
import { fromStored, type Readings } from "../../lib/readings";
import { nextRef, revisionBody } from "../../lib/revision";
import { DetailsStep, type Details } from "./DetailsStep";
import { MeasureStep } from "./MeasureStep";
import { DEFAULT_OPENINGS, TypeStep } from "./TypeStep";

type Step = "measure" | "type" | "details";

export function PositionEditor() {
  const { id = "", ref } = useParams();
  const quote = useQuote(id);
  if (quote.isPending) return <Loading />;
  if (quote.isError) return <ErrorNote message={quote.error.message} onRetry={() => void quote.refetch()} />;
  return <Editor quote={quote.data} editRef={ref} />;
}

function Editor({ quote, editRef }: { quote: QuoteDetail; editRef: string | undefined }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const save = useSaveRevision(quote.id);
  const prices = usePriceLists();
  const copyFrom = search.get("copy");
  const existing: PositionOut | undefined = quote.revision.positions.find(
    (p) => p.ref === (editRef ?? copyFrom ?? ""),
  );
  const last = lastChoices();
  const [step, setStep] = useState<Step>(existing ? "details" : "measure");
  const [readings, setReadings] = useState<Readings>(() => fromStored(existing?.readings));
  const [measured, setMeasured] = useState<{ widths: number[]; heights: number[] } | null>(
    existing?.readings ?? null,
  );
  const [colour, setColour] = useState<Colour>(existing?.colour ?? last.colour ?? "white");
  const [type, setType] = useState<string | null>(existing?.construction_type ?? null);
  const [sizeEditable, setSizeEditable] = useState(!existing?.readings && existing !== undefined);
  // The glass on offer is what this revision is priced with: its own price list, the one the
  // calculation uses. Never a draft being edited, nor a newer list the quote does not use yet.
  const pricedWith = prices.data?.find((list) => list.id === quote.revision.price_list_version_id);
  const glassBuilds = [
    ...new Set((pricedWith?.entries ?? []).filter((e) => e.item_kind === "glass").map((e) => e.item_ref)),
  ];
  const [details, setDetails] = useState<Details>(() => ({
    ref: editRef ?? nextRef(quote),
    width: existing?.width_mm ?? 0,
    height: existing?.height_mm ?? 0,
    openings: existing ? [...existing.openings] : [],
    glass: existing?.glass_build ?? last.glass ?? "",
    qty: existing?.qty ?? 1,
    installation: existing?.installation ?? {
      install: true,
      ral: false,
      old_window_removal: false,
      wall_repair: false,
    },
  }));
  const glass = details.glass || glassBuilds[0] || "";

  function saveWindow() {
    if (!type) return;
    const position: PositionIn = {
      ref: details.ref.trim(),
      construction_type: type,
      width_mm: details.width,
      height_mm: details.height,
      qty: details.qty,
      colour,
      glass_build: glass,
      openings: details.openings.length ? details.openings : (DEFAULT_OPENINGS[type] ?? ["fixed"]),
      readings: measured,
      installation: details.installation,
    };
    remember({ colour, glass });
    save.mutate(
      {
        revision: quote.revision_no,
        body: revisionBody(quote, { replace: editRef, position }),
      },
      { onSuccess: () => void navigate(`/quotes/${quote.id}`) },
    );
  }

  const stepIndex = { measure: 0, type: 1, details: 2 }[step];
  const back =
    step === "measure" || existing ? `/quotes/${quote.id}` : undefined;

  return (
    <>
      <TopBar
        title={t("position.title", { ref: details.ref })}
        subtitle={`${quote.number} · ${quote.client_name}`}
        back={back ?? `/quotes/${quote.id}`}
      />
      <ol className="flex gap-1.5 px-4 pt-3" aria-label={t(`position.step${step[0]?.toUpperCase()}${step.slice(1)}`)}>
        {(["measure", "type", "details"] as const).map((name, i) => (
          <li key={name} className="flex-1">
            <button
              type="button"
              disabled={i > stepIndex}
              onClick={() => setStep(name)}
              aria-current={i === stepIndex ? "step" : undefined}
              aria-label={t(`position.step${name[0]?.toUpperCase()}${name.slice(1)}`)}
              className={`block h-2 w-full rounded-full ${i <= stepIndex ? "bg-chalk" : "bg-plaster-deep"}`}
            />
          </li>
        ))}
      </ol>

      {step === "measure" && (
        <MeasureStep
          readings={readings}
          onReadings={setReadings}
          colour={colour}
          onColour={setColour}
          onDone={({ readings: values, measure }) => {
            setMeasured(values);
            setSizeEditable(false);
            setDetails({ ...details, width: measure.width_mm, height: measure.height_mm });
            setStep("type");
          }}
          onSkip={() => {
            setMeasured(null);
            setSizeEditable(true);
            setStep("type");
          }}
        />
      )}
      {step === "type" && (
        <TypeStep
          width={details.width || 1200}
          height={details.height || 1400}
          value={type}
          onPick={(picked) => {
            setType(picked);
            setDetails({ ...details, openings: DEFAULT_OPENINGS[picked] ?? ["fixed"] });
            setStep("details");
          }}
        />
      )}
      {step === "details" && type && (
        <DetailsStep
          type={type}
          colour={colour}
          details={{ ...details, glass }}
          glassBuilds={glassBuilds}
          sizeEditable={sizeEditable}
          busy={save.isPending}
          error={save.isError ? save.error.message : null}
          onChange={setDetails}
          onSave={saveWindow}
        />
      )}
    </>
  );
}
