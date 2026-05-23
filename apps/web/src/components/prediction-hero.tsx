import type { PredictionDisplayState } from "@/lib/show-status";
import { TONIGHT_STATUS_LABEL } from "@/lib/show-status";

type MetricCard = {
  title: string;
  avgHits: string;
  coverage: string;
};

type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  snapshotLabel: string;
  displayState: PredictionDisplayState | null;
};

type MetricPanelProps = {
  performanceWindowLabel: string;
  precisionCards: readonly [MetricCard, MetricCard, MetricCard];
};

function MetricBlock({ card }: { card: MetricCard }) {
  return (
    <div className="rounded-xl border border-outline-variant/15 bg-surface/35 px-3 py-3 md:px-4">
      <div className="border-b border-outline-variant/15 pb-2 text-center">
        <p className="font-headline text-base font-bold text-on-surface underline decoration-current decoration-2 underline-offset-4 md:text-lg">
          {card.title}
        </p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:gap-3">
        <div className="rounded-lg bg-surface-container-low/55 px-2.5 py-2.5 text-center md:rounded-xl md:px-3">
          <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-tertiary">
            Avg. Hits
          </p>
          <p className="mt-0.5 font-headline text-2xl font-bold leading-none text-tertiary md:text-3xl">
            {card.avgHits}
          </p>
          <p className="mt-1 text-[11px] leading-4 text-on-surface-variant md:text-xs md:leading-5">
            picks played
          </p>
        </div>
        <div className="rounded-lg bg-surface-container-low/55 px-2.5 py-2.5 text-center md:rounded-xl md:px-3">
          <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-primary">
            Coverage
          </p>
          <p className="mt-0.5 font-headline text-2xl font-bold leading-none text-primary md:text-3xl">
            {card.coverage}
          </p>
          <p className="mt-1 text-[11px] leading-4 text-on-surface-variant md:text-xs md:leading-5">
            setlist caught
          </p>
        </div>
      </div>
    </div>
  );
}

export function PredictionMetricPanel({
  cards,
  performanceWindowLabel,
}: {
  cards: readonly MetricCard[];
  performanceWindowLabel: string;
}) {
  return (
    <div className="editorial-chip rounded-[1.35rem] p-4 text-center md:text-left md:p-5">
      <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
        <div>
          <p className="font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-primary/85">
            Model performance
          </p>
          <h2 className="mt-1.5 font-headline text-lg font-bold text-on-surface md:text-2xl">
            How good has this model been?
          </h2>
        </div>
        <div className="rounded-xl border border-outline-variant/15 bg-surface/35 px-3 py-2.5 text-center md:min-w-56 md:px-4 md:py-3">
          <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
            Scoring Window
          </p>
          <p className="mt-0.5 font-headline text-base font-semibold text-on-surface md:text-lg">
            {performanceWindowLabel}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-2.5 md:grid-cols-3 md:gap-3">
        {cards.map((card) => (
          <MetricBlock key={card.title} card={card} />
        ))}
      </div>

    </div>
  );
}

export function PredictionHero({
  venueName,
  dateLabel,
  locationLabel,
  statusLabel,
  snapshotLabel,
  displayState,
}: Props) {
  const headlineLocation = venueName || locationLabel;
  const dateDetail = [dateLabel, locationLabel].filter(Boolean).join(" • ");

  return (
    <section className="mb-10">
      <div className="editorial-hero overflow-visible px-6 py-7 md:px-10 md:py-9">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.03),transparent_48%),radial-gradient(circle_at_top_right,rgba(255,191,105,0.16),transparent_34%)]" />
        <div className="absolute inset-y-0 right-0 w-2/5 bg-gradient-to-l from-primary-container/18 via-primary-container/8 to-transparent opacity-90" />

        <div className="relative z-10 mx-auto max-w-5xl text-center">
          <div className="mb-5 flex flex-wrap items-center justify-center gap-2">
            {statusLabel === TONIGHT_STATUS_LABEL ? (
              <span className="inline-flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-red-500">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                </span>
                {TONIGHT_STATUS_LABEL}
              </span>
            ) : displayState === "previous" ? (
              <>
                <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-label text-[10px] uppercase tracking-[0.18rem] text-amber-500">
                  {statusLabel}
                </span>
                <span className="inline-flex items-center rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-red-500">
                  Completed
                </span>
              </>
            ) : (
              <span className="inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 font-label text-[10px] uppercase tracking-[0.18rem] text-emerald-500">
                {statusLabel}
              </span>
            )}
            {displayState === "previous" && (
              <span className="inline-flex items-center rounded-full border border-outline-variant/20 bg-surface/45 px-3 py-1.5 font-label text-[10px] font-semibold uppercase tracking-[0.12rem] text-on-surface">
                <svg className="mr-1.5 size-3.5 text-on-surface-variant" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2" />
                  <circle cx="12" cy="12" r="9" />
                </svg>
                Update scheduled for afternoon
              </span>
            )}
          </div>

          <p className="font-headline text-sm uppercase tracking-[0.16em] text-primary md:text-base">
            {dateDetail}
          </p>
          <h1 className="mx-auto mt-3 max-w-4xl text-balance font-headline text-3xl font-bold uppercase tracking-[-0.05em] text-on-surface md:text-6xl">
            {headlineLocation}
          </h1>
          <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-outline-variant/15 bg-surface/35 px-3.5 py-2">
            <span className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
              Last update
            </span>
            <span className="text-sm font-medium text-on-surface/80">
              {snapshotLabel}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

export function PredictionHeroMetrics({
  performanceWindowLabel,
  precisionCards,
}: MetricPanelProps) {
  return (
    <div className="relative z-20 mx-auto -mt-6 mb-5 w-full max-w-6xl px-1 md:-mt-8 md:mb-6">
      <PredictionMetricPanel
        cards={precisionCards}
        performanceWindowLabel={performanceWindowLabel}
      />
    </div>
  );
}
