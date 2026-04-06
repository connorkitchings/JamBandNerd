import { ShowOutlookPopover } from "@/components/show-outlook-popover";
import type { PredictionRow } from "@/lib/data";

type PrecisionCard = {
  title: string;
  scope?: string;
  value: string;
  description: string;
};

type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  snapshotLabel: string;
  predictions: PredictionRow[];
  precisionCards: readonly [PrecisionCard, PrecisionCard, PrecisionCard];
  metricCaption?: string;
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

const CARD_CLASS =
  "editorial-chip relative rounded-[1.5rem] px-5 py-5 text-center backdrop-blur-sm flex min-h-[118px] flex-col justify-center";

export function PredictionHero({
  venueName,
  dateLabel,
  locationLabel,
  statusLabel,
  snapshotLabel,
  predictions,
  precisionCards,
  metricCaption,
}: Props) {
  const outlook = getOutlookSummary(predictions);
  const headlineLocation = locationLabel || venueName;
  const dateDetail = locationLabel && venueName ? `${dateLabel} • ${venueName}` : dateLabel;

  return (
    <section className="mb-10">
      <div className="editorial-hero overflow-visible px-6 py-7 md:px-10 md:py-9">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.03),transparent_48%),radial-gradient(circle_at_top_right,rgba(255,191,105,0.16),transparent_34%)]" />
        <div className="absolute inset-y-0 right-0 w-2/5 bg-gradient-to-l from-primary-container/18 via-primary-container/8 to-transparent opacity-90" />

        <div className="relative z-10 mx-auto max-w-5xl">
          <div className="mx-auto max-w-4xl text-center">
            {statusLabel === "LIVE" ? (
              <span className="inline-flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-red-500">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                </span>
                LIVE
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full border border-secondary-container/45 bg-secondary-container/35 px-3 py-1 font-label text-[10px] uppercase tracking-[0.18rem] text-on-secondary-container">
                {statusLabel}
              </span>
            )}
            <p className="mt-4 font-headline text-sm uppercase tracking-[0.16em] text-primary md:text-base">
              {dateDetail}
            </p>
            <h1 className="mx-auto mt-3 max-w-4xl text-balance font-headline text-3xl font-bold uppercase tracking-[-0.05em] text-on-surface md:text-6xl">
              {headlineLocation}
            </h1>
          </div>

          <div className="relative z-20 mx-auto mt-8 grid max-w-4xl gap-3 overflow-visible md:grid-cols-2 xl:grid-cols-4">
            <div className={`${CARD_CLASS} z-30 overflow-visible hover:z-40 focus-within:z-40`}>
              <div className="flex items-center justify-center gap-2 mb-2">
                <p className="font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant/80">
                  Show Outlook
                </p>
                <ShowOutlookPopover />
              </div>
              <p className="font-headline text-xl font-bold text-primary md:text-2xl">
                {outlook.label}
              </p>
            </div>

            <div className={`${CARD_CLASS} flex flex-col justify-center`}>
              <p className="mb-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant/80">
                {precisionCards[0].title}
              </p>
              {precisionCards[0].scope ? (
                <p className="mb-2 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-primary/85">
                  {precisionCards[0].scope}
                </p>
              ) : null}
              <div className="flex flex-col items-center justify-center gap-1">
                <p className="font-headline text-2xl font-bold text-on-surface">
                  {precisionCards[0].value}
                </p>
                <p className="font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant/80 text-center">
                  {precisionCards[0].description}
                </p>
              </div>
            </div>

            <div className={`${CARD_CLASS} flex flex-col justify-center`}>
              <p className="mb-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant/80">
                {precisionCards[1].title}
              </p>
              {precisionCards[1].scope ? (
                <p className="mb-2 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-primary/85">
                  {precisionCards[1].scope}
                </p>
              ) : null}
              <div className="flex flex-col items-center justify-center gap-1">
                <p className="font-headline text-2xl font-bold text-on-surface">
                  {precisionCards[1].value}
                </p>
                <p className="font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant/80 text-center">
                  {precisionCards[1].description}
                </p>
              </div>
            </div>

            <div className={`${CARD_CLASS} flex flex-col justify-center`}>
              <p className="mb-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant/80">
                {precisionCards[2].title}
              </p>
              {precisionCards[2].scope ? (
                <p className="mb-2 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-primary/85">
                  {precisionCards[2].scope}
                </p>
              ) : null}
              <div className="flex flex-col items-center justify-center gap-1">
                <p className="font-headline text-2xl font-bold text-on-surface">
                  {precisionCards[2].value}
                </p>
                <p className="font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant/80 text-center">
                  {precisionCards[2].description}
                </p>
              </div>
            </div>
          </div>

          {metricCaption ? (
            <p className="mx-auto mt-3 max-w-4xl text-center font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant/60">
              {metricCaption}
            </p>
          ) : null}

          <div className="mx-auto mt-5 grid max-w-4xl gap-2 border-t border-outline-variant/15 pt-4 md:grid-cols-2">
            <div className="rounded-2xl border border-outline-variant/15 bg-surface/40 px-4 py-3 text-center md:text-left">
              <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                Prediction Run
              </p>
              <p className="mt-1 text-sm text-on-surface/75">
                {snapshotLabel}
              </p>
            </div>
            <div className="rounded-2xl border border-outline-variant/15 bg-surface/40 px-4 py-3 text-center md:text-right">
              <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                Tier Note
              </p>
              <p className="mt-1 text-sm text-on-surface/75">
                Tiers reflect relative model signal, not guaranteed outcomes.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
