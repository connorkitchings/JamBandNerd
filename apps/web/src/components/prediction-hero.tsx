import type { ModelSlug } from "@/lib/config";
import type { PredictionRow } from "@/lib/data";

type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  modelSlug: ModelSlug;
  snapshotLabel: string;
  totalSongs: number;
  predictions: PredictionRow[];
};

function getOutlookSummary(predictions: PredictionRow[]) {
  if (predictions.length === 0) {
    return {
      label: "No signal",
      rotationCoreTop10: 0,
      longGapCountTop50: 0,
    };
  }

  const top10 = predictions.slice(0, 10);
  const top50 = predictions.slice(0, 50);
  const avgCurrentGap =
    top10.reduce((sum, row) => sum + (row.currentGap ?? 0), 0) /
    Math.max(top10.length, 1);
  const recentCount = top10.filter(
    (row) => (row.currentGap ?? Number.POSITIVE_INFINITY) <= 8,
  ).length;
  const longGapCountTop50 = top50.filter(
    (row) => (row.currentGap ?? 0) >= 20,
  ).length;

  if (avgCurrentGap >= 15) {
    return {
      label: "Deep cuts expected",
      rotationCoreTop10: recentCount,
      longGapCountTop50,
    };
  }

  if (recentCount >= 4 && avgCurrentGap < 8) {
    return {
      label: "Heavy rotation",
      rotationCoreTop10: recentCount,
      longGapCountTop50,
    };
  }

  if (longGapCountTop50 >= 8) {
    return {
      label: "Bust-out potential",
      rotationCoreTop10: recentCount,
      longGapCountTop50,
    };
  }

  return {
    label: "Balanced expectations",
    rotationCoreTop10: recentCount,
    longGapCountTop50,
  };
}

function getModelSpecificMetric(predictions: PredictionRow[], modelSlug: ModelSlug) {
  const top10 = predictions.slice(0, 10);

  if (modelSlug === "ckplus") {
    const gapRatios = top10
      .map((row) => row.gapRatio)
      .filter((value): value is number => value !== null);
    const avgGapRatio =
      gapRatios.length > 0
        ? gapRatios.reduce((sum, value) => sum + value, 0) / gapRatios.length
        : null;

    return {
      label: "Overdue Signal - Top 10",
      value: avgGapRatio !== null ? `${avgGapRatio.toFixed(1)}x` : "—",
      description: "avg overdue vs usual cadence",
    };
  }

  const returnWindowCount = top10.filter((row) => {
    const currentGap = row.currentGap;
    return currentGap !== null && currentGap >= 4 && currentGap <= 8;
  }).length;

  return {
    label: "Return Window - Top 10",
    value: `${returnWindowCount}/10`,
    description: "songs last played 4-8 shows ago",
  };
}

const CARD_CLASS =
  "relative rounded-2xl border border-outline-variant/20 bg-surface/82 px-5 py-4 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-sm";

export function PredictionHero({
  venueName,
  dateLabel,
  locationLabel,
  statusLabel,
  modelSlug,
  snapshotLabel,
  totalSongs,
  predictions,
}: Props) {
  const outlook = getOutlookSummary(predictions);
  const modelMetric = getModelSpecificMetric(predictions, modelSlug);

  return (
    <section className="mb-10">
      <div className="relative overflow-visible rounded-[28px] border border-outline-variant/30 bg-surface-container px-6 py-8 shadow-[0_24px_80px_rgba(0,0,0,0.08)] md:px-10 md:py-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,205,110,0.20),transparent_36%),linear-gradient(140deg,rgba(255,255,255,0.05),transparent_58%)]" />
        <div className="absolute inset-y-0 right-0 w-2/5 bg-gradient-to-l from-primary-container/16 via-primary-container/6 to-transparent opacity-90" />

        <div className="relative z-10 mx-auto max-w-5xl">
          <div className="mx-auto max-w-4xl text-center">
            <span className="inline-flex items-center rounded-full bg-secondary-container px-3 py-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-secondary-container">
              {statusLabel}
            </span>
            <p className="mt-5 font-headline text-lg uppercase tracking-[0.04em] text-primary md:text-xl">
              {dateLabel}
              {locationLabel ? ` • ${locationLabel}` : ""}
            </p>
            <h1 className="mx-auto mt-3 max-w-4xl text-balance font-headline text-4xl font-bold uppercase tracking-[-0.08em] text-on-surface md:text-6xl">
              {venueName}
            </h1>
          </div>

          <div className="relative z-20 mx-auto mt-8 grid max-w-4xl gap-3 overflow-visible md:grid-cols-2">
            <div className={`${CARD_CLASS} z-30 overflow-visible hover:z-40 focus-within:z-40`}>
              <div className="flex items-center justify-center gap-2">
                <p className="font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                  Show Outlook
                </p>
                <div className="group relative z-40">
                  <button
                    aria-label="Explain show outlook"
                    className="flex size-5 items-center justify-center rounded-full border border-outline-variant/30 text-[10px] text-on-surface-variant transition hover:border-primary hover:text-primary focus-visible:border-primary focus-visible:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    type="button"
                  >
                    i
                  </button>
                  <div className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-xl border border-outline-variant/30 bg-surface px-3 py-3 text-left text-xs leading-5 text-on-surface-variant opacity-0 shadow-xl transition group-hover:opacity-100 group-focus-within:opacity-100 md:w-72">
                    <p>A plain-language read of the current top 10 prediction board.</p>
                    <p className="mt-2">
                      <span className="font-semibold text-on-surface">Heavy rotation:</span>{" "}
                      top songs were played recently and the board leans familiar.
                    </p>
                    <p>
                      <span className="font-semibold text-on-surface">
                        Deep cuts expected:
                      </span>{" "}
                      top songs have been missing longer and the board leans less
                      frequent.
                    </p>
                    <p>
                      <span className="font-semibold text-on-surface">
                        Bust-out potential:
                      </span>{" "}
                      the wider ranked list includes more long-gap songs than usual.
                    </p>
                    <p>
                      <span className="font-semibold text-on-surface">
                        Balanced expectations:
                      </span>{" "}
                      a mix of active rotation songs and longer-gap reach candidates.
                    </p>
                  </div>
                </div>
              </div>
              <p className="mt-2 font-headline text-lg font-semibold text-primary md:text-xl">
                {outlook.label}
              </p>
            </div>

            <div className={CARD_CLASS}>
              <p className="font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                Rotation Core - Top 10
              </p>
              <div className="mt-2 flex items-baseline justify-center gap-2">
                <p className="font-headline text-lg font-semibold text-on-surface md:text-xl">
                  {outlook.rotationCoreTop10}/10
                </p>
                <p className="text-[11px] text-on-surface-variant">
                  songs played within the last 8 shows
                </p>
              </div>
            </div>

            <div className={CARD_CLASS}>
              <p className="font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                Long-Gap Watch - Top 50
              </p>
              <div className="mt-2 flex items-baseline justify-center gap-2">
                <p className="font-headline text-lg font-semibold text-on-surface md:text-xl">
                  {outlook.longGapCountTop50}/50
                </p>
                <p className="text-[11px] text-on-surface-variant">
                  songs carrying 20+ show gaps
                </p>
              </div>
            </div>

            <div className={CARD_CLASS}>
              <p className="font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                {modelMetric.label}
              </p>
              <div className="mt-2 flex items-baseline justify-center gap-2">
                <p className="font-headline text-lg font-semibold text-on-surface md:text-xl">
                  {modelMetric.value}
                </p>
                <p className="text-[11px] text-on-surface-variant">
                  {modelMetric.description}
                </p>
              </div>
            </div>
          </div>

          <div className="mx-auto mt-5 grid max-w-4xl grid-cols-1 gap-2 border-t border-outline-variant/15 pt-4 text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant md:grid-cols-2">
            <p className="text-center md:text-left">
              Songs Ranked: <span className="text-on-surface/70">{totalSongs}</span>
            </p>
            <p className="text-center md:text-right">
              Prediction Run: <span className="text-on-surface/70">{snapshotLabel}</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
