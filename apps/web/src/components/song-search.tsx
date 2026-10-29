"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { TierBadge } from "@/components/tier-badge";
import type { LikelihoodTier } from "@/lib/config";

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
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return [];

    return songs
      .filter((song) => song.songName.toLowerCase().includes(trimmed))
      .slice(0, 8);
  }, [query, songs]);

  const showResults = query.trim().length > 0;

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  return (
    <div className="relative">
      <p role="status" className="sr-only">
        {showResults
          ? `${results.length} ${results.length === 1 ? "song" : "songs"} shown`
          : ""}
      </p>
      {!isOpen ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line bg-surface-container px-4 text-sm font-semibold text-on-surface-variant transition hover:text-on-surface"
          aria-expanded={isOpen}
          aria-controls="song-search-input"
        >
          <SearchIcon />
          Search songs
        </button>
      ) : (
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">
            <SearchIcon />
          </span>
          <input
            id="song-search-input"
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Will they play…?"
            className="min-h-11 w-full rounded-md border border-line bg-surface-container py-2.5 pl-11 pr-14 text-base text-on-surface placeholder:text-on-surface-variant"
            aria-label="Search for a song"
            autoComplete="off"
            spellCheck={false}
          />
          <button
            type="button"
            onClick={() => {
              if (query) {
                setQuery("");
                inputRef.current?.focus();
                return;
              }
              setIsOpen(false);
            }}
            className="absolute right-0 top-1/2 flex size-11 -translate-y-1/2 items-center justify-center rounded-md text-on-surface-variant transition hover:text-on-surface"
            aria-label={query ? "Clear search" : "Close search"}
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
      )}

      {isOpen && showResults && results.length > 0 && (
        <div className="absolute inset-x-0 top-full z-20 mt-2 overflow-hidden rounded-xl border border-line bg-surface shadow-lg">
            <ul className="divide-y divide-line">
              {results.map((song) => {
                return (
                  <li
                    key={`${song.rank}-${song.songName}`}
                    className="flex items-center justify-between px-4 py-3 transition hover:bg-surface-container"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-base font-bold tabular-nums text-accent-text">
                        #{song.rank}
                      </span>
                      <div>
                        <p className="font-medium text-on-surface">
                          {song.songName}
                        </p>
                        <p className="text-sm text-on-surface-variant">
                          {song.currentGap !== null
                            ? `${song.currentGap} ${song.currentGap === 1 ? "show" : "shows"} ago`
                            : "Gap unknown"}
                          {song.lastPlayed ? ` · Last: ${song.lastPlayed}` : ""}
                        </p>
                      </div>
                    </div>
                    <TierBadge tier={song.tier} />
                  </li>
                );
              })}
            </ul>
        </div>
      )}
      {isOpen && showResults && results.length === 0 && (
        <div className="absolute inset-x-0 top-full z-20 mt-2 rounded-xl border border-line bg-surface px-4 py-4 shadow-lg">
          <p className="text-sm font-medium text-on-surface">No songs found</p>
          <p className="mt-1 text-sm text-on-surface-variant">
            Try a shorter title or check the full prediction board.
          </p>
        </div>
      )}
    </div>
  );
}
