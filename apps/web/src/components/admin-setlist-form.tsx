"use client";

import { useCallback, useEffect, useState } from "react";

import { parseSetlistText, type ParsedSong } from "@/lib/admin/setlist-parser";

type BandOption = { value: string; label: string };

type ExistingShow = {
  show_id: string;
  show_date: string;
  venue_name: string | null;
  city: string | null;
  state: string | null;
  source_url: string | null;
  setlistRowCount: number;
};

type SubmitResult = {
  band: string;
  showDate: string;
  showId: string;
  rows: ParsedSong[];
};

function groupBySet(rows: ParsedSong[]): Array<{ set: number; songs: ParsedSong[] }> {
  const map = new Map<number, ParsedSong[]>();
  for (const row of rows) {
    const bucket = map.get(row.set_number) ?? [];
    bucket.push(row);
    map.set(row.set_number, bucket);
  }
  return [...map.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([set, songs]) => ({ set, songs }));
}

function setLabel(set: number): string {
  return set === 99 ? "Encore" : `Set ${set}`;
}

export function AdminSetlistForm({ bands }: { bands: BandOption[] }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [isConfigured, setIsConfigured] = useState(true);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const [band, setBand] = useState(bands[0]?.value ?? "");
  const [showDate, setShowDate] = useState("");
  const [venueName, setVenueName] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [setlistText, setSetlistText] = useState("");
  const [preview, setPreview] = useState<ParsedSong[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [existingShows, setExistingShows] = useState<ExistingShow[]>([]);
  const [isLoadingShows, setIsLoadingShows] = useState(false);
  const [selectedShowId, setSelectedShowId] = useState<string | null>(null);
  const [isClearing, setIsClearing] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function checkSession() {
      try {
        const response = await fetch("/api/admin/session", { method: "GET" });
        if (!isMounted) {
          return;
        }

        if (!response.ok) {
          setIsConfigured(false);
          setIsAuthenticated(false);
          return;
        }

        const data = await response.json();
        setIsConfigured(Boolean(data.configured));
        setIsAuthenticated(Boolean(data.authenticated));
      } catch {
        if (isMounted) {
          setIsConfigured(false);
          setIsAuthenticated(false);
        }
      } finally {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      }
    }

    void checkSession();

    return () => {
      isMounted = false;
    };
  }, []);

  // Whenever band/date changes, re-resolve the existing show list so the admin
  // attaches the setlist to the correct show_id (duplicate shows are the main
  // failure mode). Reset dependent state.
  const fetchShows = useCallback(async (bandValue: string, date: string) => {
    if (!bandValue || !date) {
      setExistingShows([]);
      setSelectedShowId(null);
      return;
    }
    setIsLoadingShows(true);
    try {
      const response = await fetch(
        `/api/admin/shows?band=${encodeURIComponent(bandValue)}&date=${encodeURIComponent(date)}`,
        { method: "GET" },
      );
      if (!response.ok) {
        setExistingShows([]);
        setSelectedShowId(null);
        return;
      }
      const data = await response.json();
      const shows: ExistingShow[] = Array.isArray(data?.shows) ? data.shows : [];
      setExistingShows(shows);
      // Prefer the only match; otherwise default to "create new" so the admin
      // must explicitly confirm they want to reuse an existing show.
      setSelectedShowId(shows.length === 1 ? shows[0].show_id : null);
    } catch {
      setExistingShows([]);
      setSelectedShowId(null);
    } finally {
      setIsLoadingShows(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    void fetchShows(band, showDate);
  }, [isAuthenticated, band, showDate, fetchShows]);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!password) {
      setError("Please enter a password");
      return;
    }

    const response = await fetch("/api/admin/session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ password }),
    });

    if (response.ok) {
      setIsAuthenticated(true);
      setPassword("");
      setError("");
      return;
    }

    if (response.status === 401) {
      setError("Invalid password");
    } else if (response.status === 503) {
      setIsConfigured(false);
      setError("Admin access is not configured");
    } else {
      setError("Authentication failed");
    }
  };

  const handleLogout = async () => {
    await fetch("/api/admin/session", { method: "DELETE" });
    setIsAuthenticated(false);
    setPassword("");
  };

  const handleSetlistChange = (value: string) => {
    setSetlistText(value);
    setPreview(parseSetlistText(value));
    setResult(null);
    setMessage(null);
  };

  const resetShowFields = () => {
    setResult(null);
    setMessage(null);
  };

  const handleClearSetlist = async (showId: string) => {
    const confirmed = window.confirm(
      `Clear all setlist rows for show ${showId}? The show row itself is kept. This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }
    setIsClearing(true);
    setMessage(null);
    try {
      const response = await fetch(
        `/api/admin/setlist?band=${encodeURIComponent(band)}&showId=${encodeURIComponent(showId)}`,
        { method: "DELETE" },
      );
      const data = await response.json();
      if (response.ok) {
        setMessage({ type: "success", text: `Cleared: ${data.message}` });
        setResult(null);
        void fetchShows(band, showDate);
      } else {
        setMessage({ type: "error", text: `Error: ${data.error}` });
      }
    } catch {
      setMessage({ type: "error", text: "Failed to clear setlist" });
    } finally {
      setIsClearing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage(null);

    try {
      const response = await fetch("/api/admin/setlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          band,
          showDate,
          venueName,
          city,
          state,
          setlistText,
          showId: selectedShowId,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: "success", text: `Success: ${data.message}` });
        setResult({
          band,
          showDate,
          showId: data.showId,
          rows: Array.isArray(data.rows) ? data.rows : [],
        });
        setSetlistText("");
        setPreview([]);
        void fetchShows(band, showDate);
      } else {
        setMessage({ type: "error", text: `Error: ${data.error}` });
      }
    } catch {
      setMessage({ type: "error", text: "Failed to submit" });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isCheckingSession) {
    return (
      <div className="mx-auto max-w-md space-y-3 py-12 text-center">
        <h1 className="font-headline text-3xl font-bold text-on-surface">
          Admin Access
        </h1>
        <p className="text-sm text-on-surface-variant" role="status">
          Checking admin session...
        </p>
      </div>
    );
  }

  if (!isConfigured) {
    return (
      <div className="mx-auto max-w-xl space-y-4 py-12 text-center">
        <h1 className="font-headline text-3xl font-bold text-on-surface">
          Admin Unavailable
        </h1>
        <p className="text-sm text-on-surface-variant">
          Configure <code>ADMIN_PASSWORD</code> and{" "}
          <code>ADMIN_SESSION_SECRET</code> to enable the internal setlist
          correction route.
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md space-y-8 py-12">
        <div className="text-center">
          <h1 className="font-headline text-3xl font-bold text-on-surface">
            Admin Access
          </h1>
          <p className="mt-2 text-sm text-on-surface-variant">
            Enter the admin password to add a missing setlist.
          </p>
        </div>

        <form
          onSubmit={handlePasswordSubmit}
          className="editorial-panel space-y-4 p-5"
        >
          <div>
            <label htmlFor="password" className="sr-only">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="Enter admin password"
              className="w-full rounded-xl border border-outline-variant bg-surface px-4 py-3 text-on-surface focus:border-primary focus:outline-none"
            />
          </div>

          {error && <p className="text-sm text-error">{error}</p>}

          <button
            type="submit"
            className="w-full rounded-xl bg-primary px-4 py-3 font-label text-sm font-medium text-on-primary transition hover:bg-primary/90"
          >
            Continue
          </button>
        </form>
      </div>
    );
  }

  const createNewSelected = selectedShowId === null;
  const canSubmit =
    preview.length > 0 &&
    (createNewSelected
      ? Boolean(venueName && city && state)
      : Boolean(selectedShowId));

  return (
    <div className="mx-auto max-w-3xl space-y-8 py-8">
      <div className="editorial-hero px-6 py-7 md:px-8">
        <p className="editorial-kicker">Internal tool</p>
        <h1 className="mt-3 font-headline text-3xl font-bold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
          Add Setlist
        </h1>
        <p className="mt-2 text-sm text-on-surface-variant">
          Add a missing completed show so prediction scoring and replay can catch
          up. Always reuse an existing show when one is listed for that date to
          avoid duplicate show rows.
        </p>
        <button
          type="button"
          onClick={handleLogout}
          className="mt-4 rounded-xl border border-outline-variant/30 bg-surface px-4 py-2 font-label text-xs uppercase tracking-[0.12rem] text-on-surface transition hover:border-primary hover:text-primary"
        >
          Log out
        </button>
      </div>

      {message && (
        <div
          className={`rounded-xl px-4 py-3 ${
            message.type === "success"
              ? "bg-tertiary-container text-on-tertiary-container"
              : "bg-error-container text-on-error-container"
          }`}
        >
          {message.text}
        </div>
      )}

      {result && (
        <div className="rounded-xl border border-outline-variant p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-label text-xs font-medium text-on-surface-variant">
              Saved to show {result.showId} ({result.rows.length} songs)
            </h3>
            <div className="flex gap-2">
              <a
                href={`/last-show?band=${encodeURIComponent(result.band)}`}
                className="rounded-xl border border-outline-variant/30 bg-surface px-3 py-1.5 font-label text-xs text-on-surface transition hover:border-primary hover:text-primary"
              >
                View on site
              </a>
              <button
                type="button"
                disabled={isClearing}
                onClick={() => handleClearSetlist(result.showId)}
                className="rounded-xl border border-outline-variant/30 bg-surface px-3 py-1.5 font-label text-xs text-on-surface transition hover:border-error hover:text-error disabled:opacity-50"
              >
                {isClearing ? "Clearing..." : "Clear and re-enter"}
              </button>
            </div>
          </div>
          <div className="mt-3 space-y-2">
            {groupBySet(result.rows).map((group) => (
              <div key={group.set}>
                <p className="font-label text-[10px] uppercase tracking-[0.12rem] text-on-surface-variant">
                  {setLabel(group.set)}
                </p>
                <p className="font-mono text-sm text-on-surface">
                  {group.songs.map((s, i) => (
                    <span key={i}>
                      {s.song_name}
                      {i < group.songs.length - 1 ? (s.is_segue ? " > " : ", ") : ""}
                    </span>
                  ))}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="editorial-panel space-y-6 p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="band" className="block font-label text-xs font-medium text-on-surface-variant">
              Band
            </label>
            <select
              id="band"
              value={band}
              onChange={(e) => {
                setBand(e.target.value);
                resetShowFields();
              }}
              className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
            >
              {bands.map((b) => (
                <option key={b.value} value={b.value}>
                  {b.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="showDate" className="block font-label text-xs font-medium text-on-surface-variant">
              Show Date
            </label>
            <input
              id="showDate"
              type="date"
              value={showDate}
              onChange={(e) => {
                setShowDate(e.target.value);
                resetShowFields();
              }}
              required
              className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
            />
          </div>
        </div>

        {showDate && (
          <div className="rounded-xl border border-outline-variant p-4">
            <h3 className="font-label text-xs font-medium text-on-surface-variant">
              {isLoadingShows ? "Checking existing shows..." : "Show for this date"}
            </h3>

            {!isLoadingShows && existingShows.length === 0 && (
              <p className="mt-2 text-sm text-on-surface-variant">
                No show exists for {showDate}. Fill in the venue below to create
                one.
              </p>
            )}

            {existingShows.length > 0 && (
              <div className="mt-2 space-y-2">
                {existingShows.map((show) => {
                  const selected = selectedShowId === show.show_id;
                  return (
                    <label
                      key={show.show_id}
                      className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 transition ${
                        selected
                          ? "border-primary bg-primary/5"
                          : "border-outline-variant/40 bg-surface"
                      }`}
                    >
                      <input
                        type="radio"
                        name="existingShow"
                        value={show.show_id}
                        checked={selected}
                        onChange={() => {
                          setSelectedShowId(show.show_id);
                          resetShowFields();
                        }}
                        className="mt-1"
                      />
                      <span className="text-sm text-on-surface">
                        <span className="font-medium">{show.venue_name ?? "Unknown venue"}</span>
                        {show.city || show.state ? ` · ${[show.city, show.state].filter(Boolean).join(", ")}` : ""}
                        <span className="ml-2 text-on-surface-variant">
                          (show {show.show_id})
                        </span>
                        {show.setlistRowCount > 0 && (
                          <span className="ml-2 rounded bg-error-container px-1.5 py-0.5 font-label text-[10px] text-on-error-container">
                            {show.setlistRowCount} existing row{show.setlistRowCount === 1 ? "" : "s"} (will overwrite)
                          </span>
                        )}
                      </span>
                    </label>
                  );
                })}

                <label
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 transition ${
                    createNewSelected
                      ? "border-primary bg-primary/5"
                      : "border-outline-variant/40 bg-surface"
                  }`}
                >
                  <input
                    type="radio"
                    name="existingShow"
                    value="__new__"
                    checked={createNewSelected}
                    onChange={() => {
                      setSelectedShowId(null);
                      resetShowFields();
                    }}
                    className="mt-1"
                  />
                  <span className="text-sm text-on-surface">
                    <span className="font-medium">Create a new show</span>
                    <span className="ml-2 text-on-surface-variant">
                      (only if none of the above match)
                    </span>
                  </span>
                </label>
              </div>
            )}
          </div>
        )}

        {createNewSelected && (
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="sm:col-span-3">
              <label htmlFor="venueName" className="block font-label text-xs font-medium text-on-surface-variant">
                Venue
              </label>
              <input
                id="venueName"
                type="text"
                value={venueName}
                onChange={(e) => setVenueName(e.target.value)}
                required={createNewSelected}
                placeholder="Venue name"
                className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="city" className="block font-label text-xs font-medium text-on-surface-variant">
                City
              </label>
              <input
                id="city"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required={createNewSelected}
                placeholder="City"
                className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="state" className="block font-label text-xs font-medium text-on-surface-variant">
                State
              </label>
              <input
                id="state"
                type="text"
                value={state}
                onChange={(e) => setState(e.target.value)}
                required={createNewSelected}
                placeholder="ST"
                className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
              />
            </div>
          </div>
        )}

        <div>
          <label htmlFor="setlistText" className="block font-label text-xs font-medium text-on-surface-variant">
            Setlist
          </label>
          <textarea
            id="setlistText"
            value={setlistText}
            onChange={(e) => handleSetlistChange(e.target.value)}
            required
            rows={8}
            placeholder={`Set 1 Song A, Song B > Song C, Song D\nSet 2 Song X, Song Y\nEncore Song Z`}
            className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none font-mono text-sm"
          />
          <p className="mt-1 text-xs text-on-surface-variant">
            Format: Use Set 1 or Encore, followed by comma-separated song names. Use
            {" > "}for segues. Comma-titled songs (e.g. Lawyers, Guns, And Money) are
            kept intact.
          </p>
        </div>

        {preview.length > 0 && (
          <div className="rounded-xl border border-outline-variant p-4">
            <h3 className="font-label text-xs font-medium text-on-surface-variant">
              Preview ({preview.length} songs)
            </h3>
            <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
              {preview.map((row, idx) => (
                <div key={idx} className="flex gap-2 font-mono text-xs text-on-surface">
                  <span className="w-16 text-on-surface-variant">
                    {setLabel(row.set_number)} {row.song_position}.
                  </span>
                  <span>
                    {row.song_name}
                    {row.is_segue ? " >" : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || !canSubmit}
          className="w-full rounded-xl bg-primary px-4 py-3 font-label text-sm font-medium text-on-primary transition hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting ? "Submitting..." : "Add Setlist"}
        </button>
      </form>
    </div>
  );
}
