import type { AccuracyRow, PredictionRow } from "@/lib/data";

type Props = {
  rows: AccuracyRow[];
  predictions: PredictionRow[];
  bandLabel: string;
  modelLabel: string;
};

function getBarHeight(value: number | null) {
  const bounded = Math.max(0.1, Math.min(1, value ?? 0.15));
  return `${bounded * 100}%`;
}

function buildInsight(predictions: PredictionRow[], modelLabel: string, bandLabel: string) {
  const top = predictions[0];
  if (!top) {
    return `No live prediction rows are available yet for ${bandLabel}.`;
  }

  if ((top.currentGap ?? 0) >= 20) {
    return `The current ${modelLabel} signal suggests elevated bust-out pressure. ${top.songName} is carrying the largest overdue profile in the latest snapshot.`;
  }

  if ((top.playsPastYear ?? 0) >= 10) {
    return `The current ${modelLabel} signal is concentrated around rotation staples. ${top.songName} is leading a tight cluster of frequently played songs.`;
  }

  return `The current ${modelLabel} signal for ${bandLabel} is balanced rather than singular, with the top cluster separated by only modest model deltas.`;
}

export function DashboardAnalysis({
  rows,
  predictions,
  bandLabel,
  modelLabel,
}: Props) {
  const chartRows = rows.slice(0, 10).reverse();
  const insight = buildInsight(predictions, modelLabel, bandLabel);

  return (
    <section className="mt-16 grid grid-cols-1 gap-8 lg:grid-cols-12">
      <div className="rounded-lg bg-surface-container-low p-8 lg:col-span-8">
        <h4 className="font-headline text-xl font-bold uppercase text-on-surface">
          Recent Recall Analysis
        </h4>
        <p className="mt-2 text-sm text-on-surface-variant">
          Last completed shows for the selected band/model, using Top 10 recall as the signal.
        </p>
        <div className="mt-8 flex h-64 items-end justify-between gap-2 border-b border-outline-variant/30 pb-2">
          {chartRows.map((row, index) => (
            <div
              key={`${row.showDate}-${index}`}
              className="group relative h-full w-full rounded-t-sm bg-primary-container/20 transition-all hover:bg-primary-container"
              style={{ height: getBarHeight(row.k10Recall) }}
            />
          ))}
        </div>
        <div className="mt-4 flex justify-between font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
          <span>Older</span>
          <span>Mid Run</span>
          <span>Latest</span>
        </div>
      </div>

      <div className="space-y-4 lg:col-span-4">
        <div className="glass-card rounded-lg border border-outline-variant/10 bg-surface-container-high p-6">
          <h5 className="mb-4 font-headline text-sm font-bold uppercase text-primary">
            Archivist Insights
          </h5>
          <p className="mb-4 text-xs leading-relaxed text-on-surface-variant">{insight}</p>
          <div className="flex items-center gap-2">
            <div className="size-2 rounded-full bg-tertiary animate-pulse" />
            <span className="font-label text-[10px] uppercase text-tertiary">
              Live Processing Signal
            </span>
          </div>
        </div>
        <div className="relative h-40 overflow-hidden rounded-lg border border-outline-variant/10 bg-surface-container-high">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(176,198,255,0.25),transparent_30%),radial-gradient(circle_at_80%_30%,rgba(233,196,0,0.18),transparent_26%),radial-gradient(circle_at_50%_80%,rgba(0,88,203,0.35),transparent_34%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(17,19,22,0.2),rgba(17,19,22,0.9))]" />
        </div>
      </div>
    </section>
  );
}
