type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  modelLabel: string;
  topKLabel: string;
  snapshotLabel: string;
  confidencePercent: number | null;
  confidenceLabel: string;
};

function strokeOffset(confidencePercent: number | null) {
  const bounded = Math.max(0, Math.min(100, confidencePercent ?? 0));
  return 465 - (465 * bounded) / 100;
}

export function DashboardHero({
  venueName,
  dateLabel,
  locationLabel,
  statusLabel,
  modelLabel,
  topKLabel,
  snapshotLabel,
  confidencePercent,
  confidenceLabel,
}: Props) {
  const hasConfidence = confidencePercent !== null;
  const displayPercent = hasConfidence ? `${Math.round(confidencePercent)}` : "—";

  return (
    <section className="mb-10">
      <div className="relative min-h-[320px] overflow-hidden rounded-lg border-l-4 border-primary bg-surface-container p-8 md:p-12">
        <div className="absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-primary-container/20 to-transparent opacity-70" />
        <div className="relative z-10 grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <span className="mb-4 inline-block bg-secondary-container px-3 py-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-secondary-container">
              Upcoming Data Stream
            </span>
            <h1 className="font-headline text-4xl font-bold uppercase tracking-[-0.08em] text-on-surface md:text-6xl">
              {venueName}
            </h1>
            <p className="mb-8 mt-2 font-headline text-lg uppercase tracking-tight text-primary">
              {dateLabel}
              {locationLabel ? ` • ${locationLabel}` : ""}
            </p>
            <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Status
                </p>
                <p className="font-headline text-lg font-semibold text-primary">{statusLabel}</p>
              </div>
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Model
                </p>
                <p className="font-headline text-lg font-semibold text-on-surface">{modelLabel}</p>
              </div>
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Prediction Depth
                </p>
                <p className="font-headline text-lg font-semibold text-on-surface">{topKLabel}</p>
              </div>
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Snapshot
                </p>
                <p className="font-headline text-lg font-semibold text-on-surface">{snapshotLabel}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col items-center justify-center text-center lg:col-span-4">
            <p className="mb-6 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
              Model Confidence Score
            </p>
            <div className="relative flex size-40 items-center justify-center">
              <svg className="size-full -rotate-90">
                <circle
                  className="text-surface-container-highest"
                  cx="80"
                  cy="80"
                  fill="transparent"
                  r="74"
                  stroke="currentColor"
                  strokeWidth="10"
                />
                <circle
                  className="text-primary"
                  cx="80"
                  cy="80"
                  fill="transparent"
                  r="74"
                  stroke="currentColor"
                  strokeDasharray="465"
                  strokeDashoffset={strokeOffset(confidencePercent)}
                  strokeWidth="10"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-headline text-4xl font-bold text-on-surface">
                  {displayPercent}
                  {hasConfidence ? <span className="text-xl text-primary">%</span> : null}
                </span>
                <span className="font-label text-[9px] uppercase text-on-surface-variant">
                  {confidenceLabel}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
