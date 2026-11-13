import { useTranslation } from "react-i18next";

import type { QuoteStatus } from "../api/types";

const TONE: Record<QuoteStatus, string> = {
  draft: "bg-plaster-deep text-graphite",
  sent: "bg-chalk-tint text-chalk-deep",
  accepted: "bg-tick-tint text-tick",
  rejected: "bg-plaster-deep text-graphite-soft line-through decoration-2",
  expired: "bg-crayon-tint text-crayon",
};

export function StatusPill({ status }: { status: QuoteStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-flex min-h-7 shrink-0 items-center rounded-full px-3 text-sm font-extrabold ${TONE[status] ?? TONE.draft}`}>
      {t(`status.${status}`)}
    </span>
  );
}
