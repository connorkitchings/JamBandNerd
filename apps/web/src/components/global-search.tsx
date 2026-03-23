"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { BandSlug } from "@/lib/config";

export type GlobalSearchItem = {
  band: BandSlug;
  songName: string;
  rank: number;
};

type Props = {
  items: GlobalSearchItem[];
  bandDisplayNames: Record<string, string>;
};

function SearchIcon() {
  return (
    <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M16 16L21 21" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
    </svg>
  );
}

export function GlobalSearch({ items, bandDisplayNames }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        setIsOpen((open) => {
          if (!open) {
            // Need a tiny delay for the modal to render before focusing
            setTimeout(() => inputRef.current?.focus(), 50);
          }
          return !open;
        });
      }

      if (event.key === "Escape" && isOpen) {
        setIsOpen(false);
        setQuery("");
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const results = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return [];

    return items
      .filter((item) => item.songName.toLowerCase().includes(trimmed))
      .slice(0, 10);
  }, [query, items]);

  function handleSelect(band: string) {
    setIsOpen(false);
    setQuery("");
    router.push(`/?band=${band}`);
  }

  return (
    <>
      <button
        aria-label="Search across all bands (Cmd+K)"
        className="hidden items-center gap-2 rounded-lg border border-outline-variant/30 bg-surface-container-low px-3 py-1.5 text-sm text-on-surface-variant transition-colors hover:border-primary/50 hover:text-on-surface md:flex"
        onClick={() => {
          setIsOpen(true);
          setTimeout(() => inputRef.current?.focus(), 50);
        }}
        type="button"
      >
        <SearchIcon />
        <span>Search</span>
        <kbd className="hidden rounded bg-surface px-1.5 font-sans text-[10px] text-on-surface-variant sm:inline-block">
          ⌘K
        </kbd>
      </button>

      {/* Mobile-only icon button */}
      <button
        aria-label="Search"
        className="text-on-background/60 transition-colors hover:text-primary md:hidden"
        onClick={() => {
          setIsOpen(true);
          setTimeout(() => inputRef.current?.focus(), 50);
        }}
        type="button"
      >
        <SearchIcon />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-20 sm:pt-32">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => {
              setIsOpen(false);
              setQuery("");
            }}
          />

          {/* Modal */}
          <div
            className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-outline-variant/30 bg-surface-container shadow-2xl"
            role="dialog"
            aria-modal="true"
          >
            <div className="flex items-center border-b border-outline-variant/20 px-4">
              <span className="text-on-surface-variant">
                <SearchIcon />
              </span>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search songs across bands…"
                className="w-full bg-transparent py-4 pl-3 pr-4 font-headline text-base text-on-surface placeholder:text-on-surface-variant/50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset focus-visible:outline-none"
              />
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  setQuery("");
                }}
                className="rounded bg-surface-container-low px-2 py-1 text-[10px] uppercase tracking-wider text-on-surface-variant transition hover:bg-surface-container-highest hover:text-on-surface"
              >
                ESC
              </button>
            </div>

            {query.trim() && (
              <div className="max-h-[60vh] overflow-y-auto py-2">
                {results.length === 0 ? (
                  <div className="px-6 py-12 text-center text-sm text-on-surface-variant">
                    No songs matching &ldquo;{query.trim()}&rdquo;
                  </div>
                ) : (
                  <ul className="px-2">
                    {results.map((item, i) => (
                      <li key={`${item.band}-${item.songName}-${i}`}>
                        <button
                          className="flex w-full items-center justify-between rounded-lg px-4 py-3 text-left transition hover:bg-surface-container-highest/50 focus-visible:bg-surface-container-highest/50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
                          onClick={() => handleSelect(item.band)}
                        >
                          <div>
                            <p className="font-headline text-base font-medium text-on-surface">
                              {item.songName}
                            </p>
                            <p className="border-t-0 mt-0.5 text-xs text-on-surface-variant">
                              {bandDisplayNames[item.band] ?? item.band} • Rank #{item.rank}
                            </p>
                          </div>
                          <span className="text-primary opacity-0 transition group-hover:opacity-100">
                            →
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            
            {!query.trim() && (
              <div className="px-6 py-8 text-center text-sm text-on-surface-variant">
                Type a song name to see where it ranks across all supported bands.
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
