import Image from "next/image";
import type { PredictionRow, AccuracyRow } from "@/lib/data";

type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  modelLabel: string;
  bandLabel: string;
  snapshotLabel: string;
  totalSongs: number;
  accuracyRows: AccuracyRow[];
  predictions: PredictionRow[];
  agreementScore?: { percentage: number; matchCount: number; k: number } | null;
};

function getOutlookLabel(predictions: PredictionRow[]) {
  if (predictions.length === 0) return "No signal";

  const top10 = predictions.slice(0, 10);
  const avgGap =
    top10.reduce((sum, row) => sum + (row.currentGap ?? 0), 0) / top10.length;
  const hotCount = predictions.filter((row) => row.tier === "hot").length;
  const deepCutCount = predictions.filter((row) => row.tier === "possible").length;

  if (avgGap >= 15) return "Deep catalog energy";
  if (hotCount >= 4 && avgGap < 8) return "Heavy rotation night";
  if (deepCutCount > predictions.length * 0.4) return "Bust-out potential building";
  return "Mixed signals — balanced show expected";
}

function getTrackRecord(accuracyRows: AccuracyRow[]) {
  if (accuracyRows.length === 0) return null;

  const k10Values = accuracyRows
    .map((row) => row.k10Recall)
    .filter((v): v is number => v !== null);

  if (k10Values.length === 0) return null;

  const avg = k10Values.reduce((sum, v) => sum + v, 0) / k10Values.length;
  return Math.round(avg * 100);
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
  accuracyRows,
  predictions,
  agreementScore,
}: Props) {
  const outlookLabel = getOutlookLabel(predictions);
  const trackRecord = getTrackRecord(accuracyRows);

  return (
    <section className="mb-10">
      <div className="relative min-h-[280px] overflow-hidden rounded-lg border-l-4 border-primary bg-surface-container p-8 md:p-12">
        <div className="absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-primary-container/20 to-transparent opacity-70" />
        <div className="relative z-10 grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <span className="mb-4 inline-block bg-secondary-container px-3 py-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-secondary-container">
              {statusLabel}
            </span>
            <div className="flex items-center gap-4">
              <Image src="/logo.png" alt="JamBandNerd Logo" width={64} height={64} className="hidden rounded-full shadow-lg md:block" />
              <h1 className="font-headline text-4xl font-bold uppercase tracking-[-0.08em] text-on-surface md:text-6xl">
                {venueName}
              </h1>
            </div>
            <p className="mb-8 mt-2 font-headline text-lg uppercase tracking-tight text-primary">
              {dateLabel}
              {locationLabel ? ` • ${locationLabel}` : ""}
            </p>
            <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Band
                </p>
                <p className="font-headline text-lg font-semibold text-on-surface">{bandLabel}</p>
              </div>
              <div>
                <p className="mb-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Model
                </p>
                <div className="flex items-center gap-2">
                  <p className="font-headline text-lg font-semibold text-on-surface">{modelLabel}</p>
                  {agreementScore && (
                    <span 
                      className="rounded bg-primary/10 px-1.5 py-0.5 font-label text-[10px] font-bold uppercase tracking-wider text-primary ring-1 ring-inset ring-primary/20"
                      title={`${agreementScore.matchCount}/${agreementScore.k} Top-${agreementScore.k} songs match across models`}
                    >
                      {Math.round(agreementScore.percentage * 100)}% Match
                    </span>
                  )}
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
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Show Outlook
              </p>
              <p className="mt-2 font-headline text-lg font-semibold text-primary">
                {outlookLabel}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Model Track Record
              </p>
              {trackRecord !== null ? (
                <>
                  <p className="mt-2 font-headline text-lg font-semibold text-on-surface">
                    {trackRecord}% top-10 recall
                  </p>
                  <p className="mt-1 text-xs text-on-surface-variant">
                    Average across {accuracyRows.length} recent scored shows
                  </p>
                </>
              ) : (
                <p className="mt-2 text-sm text-on-surface-variant">
                  No scored shows yet for this model
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
