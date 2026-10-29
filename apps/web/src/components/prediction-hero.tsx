import { MetricCard } from "@/components/metric-card";
import { buildLocationLabel, formatCompactDateLabel } from "@/lib/format";
import type { MissingSetlistShow, PredictionDisplayState } from "@/lib/show-status";
import {
  shouldShowAfternoonUpdateScheduled,
  TONIGHT_STATUS_LABEL,
} from "@/lib/show-status";

type PrecisionCard = {
  title: string;
  avgHits: string;
  coverage: string;
};

type PendingNextShowInfo = {
  dateLabel: string;
  venueName: string | null;
  locationLabel: string | null;
};

type Props = {
  venueName: string;
  dateLabel: string;
  locationLabel: string;
  statusLabel: string;
  snapshotLabel: string;
  displayState: PredictionDisplayState | null;
  heroShowDate?: string | null;
  missingSetlistShows?: readonly MissingSetlistShow[];
  pendingNextShow?: PendingNextShowInfo | null;
};

export function formatMissingShowSummary(
  shows: readonly MissingSetlistShow[],
): string {
  const parts = shows.map((show) => {
    const dateText = formatCompactDateLabel(show.showDate);
    const locationText =
      buildLocationLabel([show.city, show.state ?? show.country]) ||
      show.venueName ||
      "";
    return locationText ? `${dateText} in ${locationText}` : dateText;
  });

  if (parts.length === 0) {
    return "";
  }
  if (parts.length === 1) {
    return parts[0];
  }
  if (parts.length === 2) {
    return `${parts[0]} and ${parts[1]}`;
  }
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

type MetricPanelProps = {
  performanceWindowLabel: string;
  precisionCards: readonly [PrecisionCard, PrecisionCard, PrecisionCard];
};

function PredictionMetricPanel({
  cards,
  performanceWindowLabel,
}: {
  cards: readonly PrecisionCard[];
  performanceWindowLabel: string;
}) {
  return (
    <div>
      <h2 className="text-xl font-bold text-on-surface">How good has this model been?</h2>
      <p className="mt-1 text-sm text-on-surface-variant">Scored over the {performanceWindowLabel}.</p>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {cards.map((card) => (
          <div key={card.title}>
            <h3 className="mb-2 text-base font-bold text-on-surface">{card.title}</h3>
            <div className="grid grid-cols-2 gap-3">
              <MetricCard label="Avg. hits" value={card.avgHits} hint="picks played" tone="teal" />
              <MetricCard label="Coverage" value={card.coverage} hint="setlist caught" tone="accent" />
            </div>
          </div>
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
  heroShowDate = null,
  missingSetlistShows = [],
  pendingNextShow = null,
}: Props) {
  const headlineLocation = venueName || locationLabel;
  const dateDetail = [dateLabel, locationLabel].filter(Boolean).join(" • ");
  const hasMissingSetlists = missingSetlistShows.length > 0;
  const showAfternoonScheduled = shouldShowAfternoonUpdateScheduled(
    heroShowDate,
    new Date(),
    hasMissingSetlists,
  );

  const chip = "inline-flex min-h-7 items-center gap-2 rounded-full border px-3 text-xs font-semibold uppercase tracking-[0.06em]";

  return (
    <section>
      <div className="rounded-xl border border-line bg-surface px-6 py-7 text-center md:px-10 md:py-9">
        <div className="mx-auto max-w-5xl">
          <div className="mb-5 flex flex-wrap items-center justify-center gap-2">
            {statusLabel === TONIGHT_STATUS_LABEL ? (
              <span className={`${chip} border-danger bg-danger-bg text-danger`}>
                <span aria-hidden="true" className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-danger opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-danger" />
                </span>
                {TONIGHT_STATUS_LABEL}
              </span>
            ) : displayState === "previous" ? (
              <>
                <span className={`${chip} border-accent bg-amber-bg text-accent-text`}>{statusLabel}</span>
                <span className={`${chip} border-line bg-surface-2 text-on-surface-variant`}>Completed</span>
              </>
            ) : (
              <span className={`${chip} border-teal bg-teal-bg text-teal`}>{statusLabel}</span>
            )}
            {hasMissingSetlists ? (
              <span className={`${chip} border-accent bg-amber-bg text-accent-text`}>
                Awaiting Upstream Setlist
              </span>
            ) : (
              showAfternoonScheduled && (
                <span className={`${chip} border-line bg-surface-2 text-on-surface`}>
                  <svg aria-hidden="true" className="size-3.5 text-on-surface-variant" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2" />
                    <circle cx="12" cy="12" r="9" />
                  </svg>
                  Update scheduled for afternoon
                </span>
              )
            )}
          </div>

          <p className="text-base font-semibold uppercase tracking-[0.08em] text-accent-text">
            {dateDetail}
          </p>
          <h1 className="mx-auto mt-3 max-w-4xl text-balance text-3xl font-bold text-on-surface md:text-5xl">
            {headlineLocation}
          </h1>
          <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-line bg-surface-2 px-3.5 py-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.06em] text-on-surface-variant">
              Last update
            </span>
            <span className="text-sm font-medium text-on-surface">{snapshotLabel}</span>
          </div>

          {hasMissingSetlists && (
            <div
              role="status"
              className="mx-auto mt-5 max-w-2xl rounded-xl border border-accent bg-amber-bg px-4 py-3 text-left text-sm text-on-surface md:px-5 md:py-3.5"
            >
              <p className="text-xs font-bold uppercase tracking-[0.08em] text-accent-text">
                Setlist Data Delay
              </p>
              <p className="mt-1">
                The upstream setlist data source had not published the{" "}
                <span className="font-semibold">
                  {formatMissingShowSummary(missingSetlistShows)}
                </span>{" "}
                {missingSetlistShows.length === 1 ? "setlist" : "setlists"} when
                the daily ingestion ran. Because missing setlist data affects
                song gaps and rotation calculations,{" "}
                {pendingNextShow
                  ? `predictions for the upcoming ${pendingNextShow.dateLabel}${pendingNextShow.locationLabel ? ` (${pendingNextShow.locationLabel})` : ""} show are held back until ${missingSetlistShows.length === 1 ? "that setlist is" : "those setlists are"} available.`
                  : `next-show predictions are held back and existing predictions do not yet reflect ${missingSetlistShows.length === 1 ? "that show" : "those shows"} until ${missingSetlistShows.length === 1 ? "the setlist is" : "the setlists are"} available.`}
              </p>
            </div>
          )}
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
    <PredictionMetricPanel
      cards={precisionCards}
      performanceWindowLabel={performanceWindowLabel}
    />
  );
}
