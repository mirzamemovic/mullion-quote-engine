/** The client quote and the workshop sheet as PDFs. */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { type DocumentKind, type DocumentLanguage, useDocument } from "../../api/queries";
import type { QuoteDetail } from "../../api/types";
import { Button, Note, Segmented } from "../../components/ui";
import { saveFile } from "../../lib/share";

export function Documents({
  quote,
  language,
  onLanguage,
}: {
  quote: QuoteDetail;
  language: DocumentLanguage;
  onLanguage: (lang: DocumentLanguage) => void;
}) {
  const { t } = useTranslation();
  const pdf = useDocument(quote.id, quote.revision_no);
  const [kind, setKind] = useState<DocumentKind>("quote");
  const download = (next: DocumentKind) => {
    setKind(next);
    pdf.mutate({ kind: next, lang: language }, { onSuccess: saveFile });
  };
  return (
    <section className="mx-4 mt-6 space-y-3" aria-labelledby="documents">
      <h2 id="documents" className="text-xl font-extrabold">
        {t("documents.title")}
      </h2>
      <Segmented
        label={t("documents.language")}
        value={language}
        onChange={onLanguage}
        options={[
          { value: "en", label: t("profile.en") },
          { value: "bs", label: t("profile.bs") },
        ]}
      />
      <div className="grid gap-2 sm:grid-cols-2">
        <Button tone="secondary" icon="download" busy={pdf.isPending && kind === "quote"} disabled={pdf.isPending} onClick={() => download("quote")}>
          {t("documents.quote")}
        </Button>
        <Button tone="secondary" icon="download" busy={pdf.isPending && kind === "workshop"} disabled={pdf.isPending} onClick={() => download("workshop")}>
          {t("documents.workshop")}
        </Button>
      </div>
      {pdf.isError && <Note>{pdf.error.message}</Note>}
    </section>
  );
}
