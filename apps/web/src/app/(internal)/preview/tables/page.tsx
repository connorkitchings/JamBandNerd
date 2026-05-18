import type { Metadata } from "next";

import { AccuracyTable } from "@/components/accuracy-table";
import { SongBoard } from "@/components/song-board";
import { SetlistTable } from "@/components/setlist-table";

export const metadata: Metadata = {
  title: "JamBandNerd Table Preview",
  robots: {
    index: false,
    follow: false,
  },
};

const predictionRows = [
  {
    rank: 1,
    songName: "Arcadia",
    lastPlayed: "2026-03-01 - Austin",
    currentGap: 11,
    playsPastYear: 14,
    avgGap: 8,
    recentAvgGap: 9,
    gapRatio: 1.4,
    gapZScore: 1.2,
    probability: 0.96,
    recentPlays50: 16,
    tier: "expected" as const,
  },
  {
    rank: 2,
    songName: "Wysteria Lane",
    lastPlayed: "2026-02-14 - Nashville",
    currentGap: 24,
    playsPastYear: 6,
    avgGap: 10,
    recentAvgGap: 12,
    gapRatio: 2.4,
    gapZScore: 2.0,
    probability: null,
    recentPlays50: 7,
    tier: "possible" as const,
  },
  {
    rank: 3,
    songName: "Slow Ready",
    lastPlayed: "2026-03-05 - Atlanta",
    currentGap: 3,
    playsPastYear: 12,
    avgGap: 6,
    recentAvgGap: 5,
    gapRatio: 0.5,
    gapZScore: -0.2,
    probability: 0.84,
    recentPlays50: 11,
    tier: "expected" as const,
  },
];

const accuracyRows = [
  {
    showId: "preview-2026-03-12",
    showDate: "2026-03-12",
    venueName: "The Salt Shed",
    city: "Chicago",
    state: "IL",
    recall10: 0.4,
    recall25: 0.72,
    recall50: 0.91,
    p10: 0.6,
    p25: 0.4,
    p50: 0.2,
    weightedPrecisionScore: 0.41,
  },
  {
    showId: "preview-2026-03-14",
    showDate: "2026-03-14",
    venueName: "Red Rocks Amphitheatre",
    city: "Morrison",
    state: "CO",
    recall10: 0.5,
    recall25: 0.76,
    recall50: 0.93,
    p10: 0.7,
    p25: 0.45,
    p50: 0.3,
    weightedPrecisionScore: 0.475,
  },
];

const setlistSongs = [
  { setNumber: 1, position: 1, songName: "Drive" },
  { setNumber: 1, position: 2, songName: "Tumble" },
  { setNumber: 2, position: 1, songName: "Echo of a Rose" },
  { setNumber: 2, position: 2, songName: "Hungersite" },
];

export default function TablePreviewPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <section className="rounded-xl border border-outline-variant/30 bg-surface-container p-6">
        <p className="font-label text-[10px] uppercase tracking-[0.2rem] text-on-surface-variant">
          Internal Preview
        </p>
        <h1 className="mt-2 font-headline text-3xl font-semibold text-on-surface">
          Responsive table surfaces
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
          This route exists for internal QA and smoke coverage so dense data modules can be checked
          on mobile without requiring live Supabase data.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="font-headline text-xl font-semibold text-on-surface">Song board</h2>
        <SongBoard rows={predictionRows} />
      </section>

      <section className="space-y-4">
        <h2 className="font-headline text-xl font-semibold text-on-surface">Accuracy table</h2>
        <AccuracyTable rows={accuracyRows} />
      </section>

      <section className="space-y-4">
        <h2 className="font-headline text-xl font-semibold text-on-surface">Setlist table</h2>
        <SetlistTable songs={setlistSongs} />
      </section>
    </div>
  );
}
