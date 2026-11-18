/** A label and an amount, as a row of a price explanation. */


export function Row({ label, value, strong, soft }: { label: string; value: string; strong?: boolean; soft?: boolean }) {
  return (
    <div className={`flex items-baseline justify-between gap-4 ${soft ? "pl-3 text-graphite-soft" : ""} ${strong ? "font-bold" : ""}`}>
      <dt className="min-w-0">{label}</dt>
      <dd className="figure shrink-0 text-figure-sm">{value}</dd>
    </div>
  );
}
