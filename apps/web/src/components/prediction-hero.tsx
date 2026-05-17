import { TONIGHT_STATUS_LABEL } from "@/lib/show-status";

type PrecisionCard = {
  title: string;
  precision: string;
  recall: string;
};

type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  snapshotLabel: string;
  performanceWindowLabel: string;
  precisionCards: readonly [PrecisionCard, PrecisionCard];
};

function MetricBlock({ card }: { card: PrecisionCard }) {
  return (
    <div className="rounded-2xl border border-outline-variant/15 bg-surface/35 px-4 py-4">
      <div className="text-center">
        <p className="font-headline text-lg font-bold text-on-surface">
          {card.title}
        </p>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4">
        <div className="text-center">
          <p className="font-label text-[9px] uppercase tracking-[0.14rem] text-on-surface-variant">
            Avg. Hits
          </p>
          <p className="mt-1 font-headline text-2xl font-bold text-on-surface md:text-3xl">
            {card.precision}
          </p>
          <p className="mt-1 text-xs leading-5 text-on-surface-variant">
            picks played
          </p>
        </div>
        <div className="text-center">
          <p className="font-label text-[9px] uppercase tracking-[0.14rem] text-on-surface-variant">
            Recall
          </p>
          <p className="mt-1 font-headline text-2xl font-bold text-primary md:text-3xl">
            {card.recall}
          </p>
          <p className="mt-1 text-xs leading-5 text-on-surface-variant">
            setlist caught
          </p>
        </div>
      </div>
    </div>
  );
}

function MetricPanel({
  cards,
  performanceWindowLabel,
}: {
  cards: readonly PrecisionCard[];
  performanceWindowLabel: string;
}) {
  return (
    <div className="editorial-chip rounded-[1.5rem] p-5 text-left md:p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-primary/85">
            Model performance
          </p>
          <h2 className="mt-2 font-headline text-xl font-bold text-on-surface md:text-2xl">
            How good has this model been?
          </h2>
        </div>
        <p className="rounded-full border border-outline-variant/15 bg-surface/35 px-3 py-1.5 font-label text-[10px] uppercase tracking-[0.14rem] text-on-surface-variant">
          {performanceWindowLabel}
        </p>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
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
  performanceWindowLabel,
  precisionCards,
}: Props) {
  const headlineLocation = locationLabel || venueName;
  const dateDetail = locationLabel && venueName ? `${dateLabel} • ${venueName}` : dateLabel;

  return (
    <section className="mb-10">
      <div className="editorial-hero overflow-visible px-6 py-7 md:px-10 md:py-9">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.03),transparent_48%),radial-gradient(circle_at_top_right,rgba(255,191,105,0.16),transparent_34%)]" />
        <div className="absolute inset-y-0 right-0 w-2/5 bg-gradient-to-l from-primary-container/18 via-primary-container/8 to-transparent opacity-90" />

        <div className="relative z-10 mx-auto max-w-5xl">
          <div className="mx-auto max-w-4xl text-center">
            {statusLabel === TONIGHT_STATUS_LABEL ? (
              <span className="inline-flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-red-500">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                </span>
                {TONIGHT_STATUS_LABEL}
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

          <div className="relative z-20 mx-auto mt-8 max-w-4xl">
            <MetricPanel
              cards={precisionCards}
              performanceWindowLabel={performanceWindowLabel}
            />
          </div>

          <div className="mx-auto mt-5 grid max-w-4xl gap-2 border-t border-outline-variant/15 pt-4 md:grid-cols-[0.75fr_1.25fr]">
            <div className="rounded-2xl border border-outline-variant/15 bg-surface/40 px-4 py-3 text-center md:text-left">
              <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                Prediction Run
              </p>
              <p className="mt-1 text-sm text-on-surface/75">
                {snapshotLabel}
              </p>
            </div>
            <div className="rounded-2xl border border-outline-variant/15 bg-surface/40 px-4 py-3 text-center md:text-left">
              <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                How To Read It
              </p>
              <p className="mt-1 text-sm leading-6 text-on-surface/75">
                Avg. hits is the average number of model picks that were
                played. Recall is how much of the actual setlist the model
                caught.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
