"use client";

import { useMemo, useState } from "react";

import { TIER_CONFIG, type LikelihoodTier } from "@/lib/config";

type SongResult = {
  rank: number;
  songName: string;
  tier: LikelihoodTier;
  currentGap: number | null;
  lastPlayed: string | null;
};

type Props = {
  songs: SongResult[];
};

function SearchIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M16 16L21 21" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
    </svg>
  );
}

export function SongSearch({ songs }: Props) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return [];

    return songs
      .filter((song) => song.songName.toLowerCase().includes(trimmed))
      .slice(0, 8);
  }, [query, songs]);

  const showResults = query.trim().length > 0;

  return (
    <div className="relative">
      <div className="relative">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">
          <SearchIcon />
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Will they play…?"
          className="w-full rounded-xl border border-outline-variant/30 bg-surface-container py-3.5 pl-11 pr-4 font-headline text-sm text-on-surface placeholder:text-on-surface-variant/50 transition focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
          aria-label="Search for a song"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-on-surface-variant transition hover:text-on-surface"
            aria-label="Clear search"
          >
            ✕
          </button>
        )}
      </div>

      {showResults && results.length > 0 && (
        <div className="absolute inset-x-0 top-full z-20 mt-2 overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-container-high shadow-xl">
            <ul className="divide-y divide-outline-variant/15">
              {results.map((song) => {
                const tierConfig = TIER_CONFIG[song.tier];
                return (
                  <li
                    key={`${song.rank}-${song.songName}`}
                    className="flex items-center justify-between px-4 py-3 transition hover:bg-surface-container-highest/50"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-headline text-lg font-bold text-primary tabular-nums">
                        #{song.rank}
                      </span>
                      <div>
                        <p className="font-headline font-medium text-on-surface">
                          {song.songName}
                        </p>
                        <p className="text-xs text-on-surface-variant">
                          {song.currentGap !== null
                            ? `${song.currentGap} ${song.currentGap === 1 ? "show" : "shows"} ago`
                            : "Gap unknown"}
                          {song.lastPlayed ? ` · Last: ${song.lastPlayed}` : ""}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`rounded-full border px-2.5 py-1 font-label text-[10px] font-medium uppercase tracking-[0.14rem] ${tierConfig.badgeClassName}`}
                    >
                      {tierConfig.label}
                    </span>
                  </li>
                );
              })}
            </ul>
        </div>
      )}
    </div>
  );
}
