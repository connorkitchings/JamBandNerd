import type { PredictionRow, ModelAgreement } from "@/lib/data";

type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  modelLabel: string;
  bandLabel: string;
  snapshotLabel: string;
  totalSongs: number;
  predictions: PredictionRow[];
  agreementScore?: ModelAgreement | null;
};

function getOutlookLabel(predictions: PredictionRow[]) {
  if (predictions.length === 0) return "No signal";

  const top10 = predictions.slice(0, 10);
  const avgRecentGap =
    top10.reduce(
      (sum, row) => sum + (row.recentAvgGap ?? row.avgGap ?? 0),
      0
    ) / top10.length;
  const hotCount = predictions.filter((row) => row.tier === "hot").length;
  const deepCutCount = predictions.filter((row) => row.tier === "possible").length;

  if (avgRecentGap >= 15) return "Deep cuts expected";
  if (hotCount >= 4 && avgRecentGap < 8) return "Heavy rotation";
  if (deepCutCount > predictions.length * 0.4) return "Bust-out potential";
  return "Balanced expectations";
}

export function PredictionHero({
  venueName,
  dateLabel,
  locationLabel,
  statusLabel,
  modelLabel,
  bandLabel,
  snapshotLabel,
  totalSongs,
  predictions,
  agreementScore,
}: Props) {
  const outlookLabel = getOutlookLabel(predictions);

  return (
    <section className="mb-10">
      <div className="relative min-h-[280px] overflow-hidden rounded-lg border-l-4 border-primary bg-surface-container p-8 md:p-12">
        <div className="absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-primary-container/20 to-transparent opacity-70" />
        <div className="relative z-10 grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <span className="mb-4 inline-block bg-secondary-container px-3 py-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-secondary-container">
              {statusLabel}
            </span>
            <h1 className="mb-8 mt-2 font-headline text-4xl font-bold uppercase tracking-[-0.08em] text-on-surface md:text-6xl">
              {venueName}
            </h1>
            <p className="mb-8 mt-2 font-headline text-lg uppercase tracking-tight text-primary">
              {dateLabel}
              {locationLabel ? ` • ${locationLabel}` : ""}
            </p>
            <div className="grid grid-cols-2 gap-6">
              <div className="md:hidden">
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Band
                </p>
                <p className="font-headline text-lg font-semibold text-on-surface">{bandLabel}</p>
              </div>
              <div className="md:hidden">
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Model
                </p>
                <div className="flex items-center gap-2">
                  <p className="font-headline text-lg font-semibold text-on-surface">{modelLabel}</p>
                </div>
              </div>
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Songs Ranked
                </p>
                <p className="font-headline text-lg font-semibold text-on-surface">{totalSongs}</p>
              </div>
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Snapshot
                </p>
                <p className="font-headline text-lg font-semibold text-on-surface">{snapshotLabel}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4 lg:col-span-4">
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5">
              <div className="flex items-center gap-2">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Show Outlook
                </p>
                <span
                  className="text-[10px] text-on-surface-variant"
                  title="Based on songs in the top 10 predictions"
                >
                  ⓘ
                </span>
              </div>
              <p className="mt-2 font-headline text-lg font-semibold text-primary">
                {outlookLabel}
              </p>

              {agreementScore && (
                <div className="mt-4 border-t border-outline-variant/20 pt-4">
                  <div className="mb-2 flex items-center gap-2">
                    <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                      Model Agreement
                    </p>
                    <span 
                      className="rounded bg-primary/10 px-1.5 py-0.5 font-label text-[10px] font-bold uppercase tracking-wider text-primary ring-1 ring-inset ring-primary/20"
                      title={`${Math.round(agreementScore.composite * 100)}% weighted agreement across models`}
                    >
                      {Math.round(agreementScore.composite * 100)}% Match
                    </span>
                  </div>
                  <div className="flex gap-3">
                    <span className="text-[10px] text-on-surface-variant">
                      <span className="font-semibold">{agreementScore.top10.matchCount}/{agreementScore.top10.total}</span> top-10
                    </span>
                    <span className="text-[10px] text-on-surface-variant">
                      <span className="font-semibold">{agreementScore.top25.matchCount}/{agreementScore.top25.total}</span> top-25
                    </span>
                    <span className="text-[10px] text-on-surface-variant">
                      <span className="font-semibold">{agreementScore.top50.matchCount}/{agreementScore.top50.total}</span> top-50
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
