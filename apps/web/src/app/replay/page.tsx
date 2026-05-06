import type { Metadata } from "next";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { ExpandablePanel } from "@/components/expandable-panel";
import { PageHero } from "@/components/page-hero";
import { ReplayShowSelect } from "@/components/replay-show-select";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
} from "@/components/responsive-table";
import { SectionCard } from "@/components/section-card";
import { SetlistColumns } from "@/components/setlist-columns";
import { MODEL_CONFIG } from "@/lib/config";
import {
  bandEntryBySlug,
  getBands,
  getReplaySnapshot,
  resolveBandSelection,
  type PredictionRow,
} from "@/lib/data";
import {
  formatCompactDateLabel,
  formatPercent,
  formatTimestampLabel,
} from "@/lib/format";
import { normalizeSongName } from "@/lib/song-board";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    date?: string;
    modelA?: string;
    modelB?: string;
  }>;
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;
  const dateStr = params.date ? ` (${formatCompactDateLabel(params.date)})` : "";

  return {
    title: `${bandName} Replay${dateStr} | JamBandNerd`,
    description: `Review two retained model boards against the actual setlist for a completed ${bandName} show.`,
  };
}

function computeTopKRecall(
  rows: PredictionRow[],
  actualSongs: Set<string>,
  k: number,
) {
  if (actualSongs.size === 0) {
    return null;
  }

  let hits = 0;
  for (let index = 0; index < Math.min(k, rows.length); index += 1) {
    if (actualSongs.has(normalizeSongName(rows[index].songName))) {
      hits += 1;
    }
  }

  return hits / actualSongs.size;
}

function computeTopKHits(
  rows: PredictionRow[],
  actualSongs: Set<string>,
  k: number,
) {
  let hits = 0;
  for (let index = 0; index < Math.min(k, rows.length); index += 1) {
    if (actualSongs.has(normalizeSongName(rows[index].songName))) {
      hits += 1;
    }
  }
  return hits;
}

function wasPlayed(songName: string | null, actualSongs: Set<string>) {
  return songName ? actualSongs.has(normalizeSongName(songName)) : false;
}

function renderPlayedLabel(
  label: string,
  exists: boolean,
  played: boolean,
  accentClassName: string,
) {
  if (!exists) {
    return (
      <span className="rounded-full border border-outline-variant/20 bg-surface px-2 py-1 font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
        No pick
      </span>
    );
  }

  return (
    <span
      className={`rounded-full border px-2 py-1 font-label text-[9px] uppercase tracking-[0.16rem] ${
        played
          ? `${accentClassName} border-current/25 bg-current/12`
          : "border-outline-variant/20 bg-surface text-on-surface-variant"
      }`}
      aria-label={played ? `${label} prediction was played` : `${label} prediction was not played`}
    >
      {played ? "Hit" : "Miss"}
    </span>
  );
}

export default async function ReplayPage({ searchParams }: Props) {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  if (bandsResult.status === "ready" && bandSelection.isInvalid) {
    return (
      <DataState
        title="Band not found"
        body={`No active band found for slug "${bandSelection.requestedSlug}". Select a supported band from the navigation.`}
      />
    );
  }

  const selectedBand =
    bandsResult.status === "ready" ? bandSelection.bandEntry?.slug : params.band;
  const state = await getReplaySnapshot(
    selectedBand,
    params.date,
    params.modelA,
    params.modelB,
    50,
  );

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the replay route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Replay query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No replay history available"
        body="No retained scored prediction runs were found for both models on the selected band."
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;
  const show = state.replay.show;
  const primaryModel = state.replay.modelA;
  const secondaryModel = state.replay.modelB;
  const primarySnapshot = state.replay.snapshots[primaryModel] ?? null;
  const secondarySnapshot = state.replay.snapshots[secondaryModel] ?? null;
  const primaryRows = primarySnapshot?.predictions ?? [];
  const secondaryRows = secondarySnapshot?.predictions ?? [];
  const primaryLabel = MODEL_CONFIG[primaryModel].displayName;
  const secondaryLabel = MODEL_CONFIG[secondaryModel].displayName;
  const actualSongs = new Set(
    (state.replay.setlist?.songs ?? []).map((song) => normalizeSongName(song.songName)),
  );
  const locationCity = show?.city ?? "Unavailable";
  const locationRegion = show?.state ?? show?.country ?? "Unavailable";

  const primaryTop10Hits = computeTopKHits(primaryRows, actualSongs, 10);
  const secondaryTop10Hits = computeTopKHits(secondaryRows, actualSongs, 10);
  const primaryByRank = new Map(primaryRows.map((row) => [row.rank, row] as const));
  const secondaryByRank = new Map(secondaryRows.map((row) => [row.rank, row] as const));
  const maxRank = Math.max(
    primaryRows[primaryRows.length - 1]?.rank ?? 0,
    secondaryRows[secondaryRows.length - 1]?.rank ?? 0,
  );
  const replayRows = Array.from({ length: maxRank }, (_, index) => {
    const rank = index + 1;
    const primaryRow = primaryByRank.get(rank) ?? null;
    const secondaryRow = secondaryByRank.get(rank) ?? null;

    return {
      rank,
      primarySong: primaryRow?.songName ?? null,
      primaryPlayed: wasPlayed(primaryRow?.songName ?? null, actualSongs),
      secondarySong: secondaryRow?.songName ?? null,
      secondaryPlayed: wasPlayed(secondaryRow?.songName ?? null, actualSongs),
    };
  });
  const mobileReplayRows = replayRows.slice(0, 10);
  const remainingReplayRows = replayRows.slice(10);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav
        band={state.band}
        model={primaryModel}
        bands={bands}
        pathname="/replay"
        hideSecondary
        bandLinks={bands.map((item) => ({
          href: state.replay.selectedDate
            ? `/replay?band=${item.slug}&date=${state.replay.selectedDate}&modelA=${primaryModel}&modelB=${secondaryModel}`
            : `/replay?band=${item.slug}&modelA=${primaryModel}&modelB=${secondaryModel}`,
          label: item.displayName,
          active: item.slug === state.band,
        }))}
      />

      <PageHero
        kicker="Replay"
        eyebrow=""
        title={`${bandName} prediction replay`}
        description="Review one completed show with both retained model boards aligned to the same night. Replay uses the historically retained scored snapshot for that show, so its prediction cutoff can be earlier than the live predictions page for the same calendar date."
        descriptionClassName="max-w-4xl"
      />

      <SectionCard title="Actual Setlist">
        {state.replay.setlist ? (
          <div className="space-y-5">
            <ReplayShowSelect
              band={state.band}
              selectedDate={state.replay.selectedDate}
              options={state.replay.availableShows}
              label="Select show"
            />
            <div className="grid gap-3 md:grid-cols-2 md:gap-4">
              <div className="min-w-0 rounded-xl border border-outline-variant/20 bg-surface-container-low p-3 md:p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Venue
                </p>
                <p className="mt-2 text-xs leading-5 text-on-surface md:text-sm">
                  {show?.venueName ?? "Unavailable"}
                </p>
              </div>
              <div className="min-w-0 rounded-xl border border-outline-variant/20 bg-surface-container-low p-3 md:p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Location
                </p>
                <p className="mt-2 text-xs leading-5 text-on-surface md:text-sm">
                  {locationCity}
                  {locationRegion !== "Unavailable" ? `, ${locationRegion}` : ""}
                </p>
              </div>
            </div>
            <SetlistColumns songs={state.replay.setlist.songs} />
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low p-5 text-center">
                <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                  Actual setlist
                </p>
                <p className="mt-4 font-headline text-4xl font-semibold tracking-[-0.04em] text-on-surface">
                  {state.replay.setlist.songs.length}
                </p>
                <p className="mt-1 text-sm text-on-surface">songs played</p>
              </div>
              <div className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low p-5 text-center">
                <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                  {primaryLabel} hits
                </p>
                <div className="mt-4 flex items-end justify-center gap-3">
                  <p className="font-headline text-4xl font-semibold tracking-[-0.04em] text-primary">
                    {primaryRows.length > 0 ? primaryTop10Hits : "—"}
                  </p>
                  <p className="pb-1 text-[11px] uppercase tracking-[0.14rem] text-on-surface-variant">
                    top 10
                  </p>
                </div>
                <p className="mt-2 text-sm text-on-surface">
                  {formatPercent(computeTopKRecall(primaryRows, actualSongs, 10))} accuracy
                </p>
              </div>
              <div className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low p-5 text-center">
                <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                  {secondaryLabel} hits
                </p>
                <div className="mt-4 flex items-end justify-center gap-3">
                  <p className="font-headline text-4xl font-semibold tracking-[-0.04em] text-tertiary">
                    {secondaryRows.length > 0 ? secondaryTop10Hits : "—"}
                  </p>
                  <p className="pb-1 text-[11px] uppercase tracking-[0.14rem] text-on-surface-variant">
                    top 10
                  </p>
                </div>
                <p className="mt-2 text-sm text-on-surface">
                  {formatPercent(computeTopKRecall(secondaryRows, actualSongs, 10))} accuracy
                </p>
              </div>
            </div>
          </div>
        ) : (
          <DataState
            title="No setlist found"
            body="A retained replay snapshot exists, but the matching setlist payload was not found."
          />
        )}
      </SectionCard>

      <SectionCard title={`${primaryLabel} vs ${secondaryLabel}`}>
        {primarySnapshot && secondarySnapshot ? (
          <div className="space-y-5">
            <p className="text-sm leading-6 text-on-surface-variant">
              Read both retained boards by rank and check whether each pick made the actual setlist.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {[
                { label: primaryLabel, snapshot: primarySnapshot, accent: "text-primary" },
                { label: secondaryLabel, snapshot: secondarySnapshot, accent: "text-tertiary" },
              ].map(({ label, snapshot, accent }) => (
                <div
                  key={label}
                  className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low p-4"
                >
                  <p className={`font-label text-[10px] uppercase tracking-[0.16rem] ${accent}`}>
                    {label} snapshot
                  </p>
                  <dl className="mt-3 space-y-2 text-sm text-on-surface">
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-on-surface-variant">Snapshot captured</dt>
                      <dd>{formatTimestampLabel(snapshot?.predictedAt ?? null)}</dd>
                    </div>
                  </dl>
                </div>
              ))}
            </div>
            <div className="space-y-3 md:hidden" data-testid="replay-comparison-cards">
              {mobileReplayRows.map((row) => (
                <article
                  key={row.rank}
                  className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Rank {row.rank}
                    </p>
                    <div className="flex gap-2">
                      {row.primaryPlayed ? (
                        <span className="rounded-full border border-primary/25 bg-primary/12 px-2.5 py-1 font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                          {primaryLabel} hit
                        </span>
                      ) : null}
                      {row.secondaryPlayed ? (
                        <span className="rounded-full border border-tertiary/25 bg-tertiary/12 px-2.5 py-1 font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                          {secondaryLabel} hit
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3">
                    <div className="rounded-2xl bg-surface/70 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                            {primaryLabel}
                          </p>
                          <p
                            className={`mt-2 font-headline text-base font-medium ${
                              row.primaryPlayed ? "text-primary" : "text-on-surface"
                            }`}
                          >
                            {row.primarySong ?? "—"}
                          </p>
                        </div>
                        {renderPlayedLabel(
                          primaryLabel,
                          Boolean(row.primarySong),
                          row.primaryPlayed,
                          "text-primary",
                        )}
                      </div>
                    </div>

                    <div className="rounded-2xl bg-surface/70 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                            {secondaryLabel}
                          </p>
                          <p
                            className={`mt-2 font-headline text-base font-medium ${
                              row.secondaryPlayed ? "text-tertiary" : "text-on-surface"
                            }`}
                          >
                            {row.secondarySong ?? "—"}
                          </p>
                        </div>
                        {renderPlayedLabel(
                          secondaryLabel,
                          Boolean(row.secondarySong),
                          row.secondaryPlayed,
                          "text-tertiary",
                        )}
                      </div>
                    </div>
                  </div>
                </article>
              ))}

              {remainingReplayRows.length > 0 ? (
                <ExpandablePanel
                  bodyClassName="space-y-3 px-3 pt-3"
                  buttonClassName="w-full rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4 text-center font-headline text-sm uppercase tracking-[0.12em] text-on-surface"
                  containerClassName="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low"
                >
                  {remainingReplayRows.map((row) => (
                    <article
                      key={row.rank}
                      className="rounded-[1.2rem] border border-outline-variant/20 bg-surface/70 px-4 py-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                          Rank {row.rank}
                        </p>
                        <div className="flex gap-2">
                          {row.primaryPlayed ? (
                            <span className="rounded-full border border-primary/25 bg-primary/12 px-2.5 py-1 font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                              {primaryLabel} hit
                            </span>
                          ) : null}
                          {row.secondaryPlayed ? (
                            <span className="rounded-full border border-tertiary/25 bg-tertiary/12 px-2.5 py-1 font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                              {secondaryLabel} hit
                            </span>
                          ) : null}
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3">
                        <div className="rounded-2xl bg-surface-container px-3 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                                {primaryLabel}
                              </p>
                              <p
                                className={`mt-2 font-headline text-base font-medium ${
                                  row.primaryPlayed ? "text-primary" : "text-on-surface"
                                }`}
                              >
                                {row.primarySong ?? "—"}
                              </p>
                            </div>
                            {renderPlayedLabel(
                              primaryLabel,
                              Boolean(row.primarySong),
                              row.primaryPlayed,
                              "text-primary",
                            )}
                          </div>
                        </div>

                        <div className="rounded-2xl bg-surface-container px-3 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                                {secondaryLabel}
                              </p>
                              <p
                                className={`mt-2 font-headline text-base font-medium ${
                                  row.secondaryPlayed ? "text-tertiary" : "text-on-surface"
                                }`}
                              >
                                {row.secondarySong ?? "—"}
                              </p>
                            </div>
                            {renderPlayedLabel(
                              secondaryLabel,
                              Boolean(row.secondarySong),
                              row.secondaryPlayed,
                              "text-tertiary",
                            )}
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </ExpandablePanel>
              ) : null}
            </div>

            <div className="hidden md:block">
              <ResponsiveTableFrame
                minWidthClassName="min-w-[780px]"
                testId="replay-comparison"
              >
                <thead className="bg-surface-container-low text-on-surface-variant">
                  <tr>
                    <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Rank</th>
                    <th className={TABLE_HEAD_CLASS}>{primaryLabel}</th>
                    <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center`}>
                      Played
                    </th>
                    <th className={TABLE_HEAD_CLASS}>{secondaryLabel}</th>
                    <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center`}>
                      Played
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
                  {replayRows.map((row) => (
                    <tr key={row.rank} className="odd:bg-surface-container-low/30">
                      <td
                        className={`${TABLE_CELL_CLASS} whitespace-nowrap font-headline font-semibold text-on-surface-variant`}
                      >
                        {row.rank}
                      </td>
                      <td className={TABLE_CELL_CLASS}>
                        <span
                          className={`font-headline font-medium ${
                            row.primaryPlayed ? "text-primary" : "text-on-surface"
                          }`}
                        >
                          {row.primarySong ?? "—"}
                        </span>
                      </td>
                      <td className={`${TABLE_CELL_CLASS} text-center`}>
                        <span
                          className={`font-label text-[10px] font-semibold uppercase tracking-[0.16rem] ${
                            row.primarySong
                              ? row.primaryPlayed
                                ? "text-primary"
                                : "text-on-surface-variant"
                              : "text-on-surface-variant"
                          }`}
                          aria-label={
                            row.primarySong
                              ? row.primaryPlayed
                                ? `${primaryLabel} prediction was played`
                                : `${primaryLabel} prediction was not played`
                              : `No ${primaryLabel} prediction`
                          }
                        >
                          {row.primarySong ? (row.primaryPlayed ? "✓" : "") : "—"}
                        </span>
                      </td>
                      <td className={TABLE_CELL_CLASS}>
                        <span
                          className={`font-headline font-medium ${
                            row.secondaryPlayed ? "text-tertiary" : "text-on-surface"
                          }`}
                        >
                          {row.secondarySong ?? "—"}
                        </span>
                      </td>
                      <td className={`${TABLE_CELL_CLASS} text-center`}>
                        <span
                          className={`font-label text-[10px] font-semibold uppercase tracking-[0.16rem] ${
                            row.secondarySong
                              ? row.secondaryPlayed
                                ? "text-primary"
                                : "text-on-surface-variant"
                              : "text-on-surface-variant"
                          }`}
                          aria-label={
                            row.secondarySong
                              ? row.secondaryPlayed
                                ? `${secondaryLabel} prediction was played`
                                : `${secondaryLabel} prediction was not played`
                              : `No ${secondaryLabel} prediction`
                          }
                        >
                          {row.secondarySong ? (row.secondaryPlayed ? "✓" : "") : "—"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </ResponsiveTableFrame>
            </div>
          </div>
        ) : (
          <DataState
            title="Replay snapshots missing"
            body="This show is in the replay window, but both retained model boards were not available for table comparison."
          />
        )}
      </SectionCard>
    </div>
  );
}
