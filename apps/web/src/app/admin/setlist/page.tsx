"use client";

import { useState } from "react";

const ACTIVE_BANDS = [
  { value: "wsp", label: "Widespread Panic" },
  { value: "goose", label: "Goose" },
  { value: "phish", label: "Phish" },
  { value: "billy", label: "Billy Strings" },
  { value: "eggy", label: "Eggy" },
  { value: "um", label: "Umphrey's McGee" },
];

export default function AdminSetlistPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const [band, setBand] = useState("wsp");
  const [showDate, setShowDate] = useState("");
  const [venueName, setVenueName] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [setlistText, setSetlistText] = useState("");
  const [preview, setPreview] = useState<Array<{ set: number; position: number; song: string }>>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!password) {
      setError("Please enter a password");
      return;
    }

    const response = await fetch("/api/admin/setlist", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${password}`,
      },
      body: JSON.stringify({ test: true }),
    });

    if (response.status === 401) {
      setError("Invalid password");
    } else if (response.status === 400) {
      setIsAuthenticated(true);
      setError("");
    } else if (response.status === 500 && (await response.json()).error === "Missing required fields") {
      setIsAuthenticated(true);
      setError("");
    } else {
      setError("Authentication failed");
    }
  };

  const parsePreview = (text: string) => {
    const rows: Array<{ set: number; position: number; song: string }> = [];
    const lines = text.split("\n").map((ln) => ln.trim()).filter(Boolean);

    for (const line of lines) {
      let setNumber: number | null = null;
      let songsPart: string | null = null;

      const setMatch = line.match(/^Set\s*(\d+)\s+(.*)$/i);
      if (setMatch) {
        setNumber = parseInt(setMatch[1], 10);
        songsPart = setMatch[2];
      } else {
        const encoreMatch = line.match(/^Encore\s+(.*)$/i);
        if (encoreMatch) {
          setNumber = 99;
          songsPart = encoreMatch[1];
        }
      }

      if (setNumber === null || songsPart === null) {
        continue;
      }

      const items = songsPart.split(",").map((s) => s.trim()).filter(Boolean);
      let pos = 1;

      for (const item of items) {
        const parts = item.split(">").map((p) => p.trim()).filter(Boolean);
        for (const part of parts) {
          rows.push({
            set: setNumber,
            position: pos,
            song: part.replace(/[\u2018\u2019]/g, "'").trim(),
          });
          pos++;
        }
      }
    }

    setPreview(rows);
  };

  const handleSetlistChange = (value: string) => {
    setSetlistText(value);
    parsePreview(value);
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
          Authorization: `Bearer ${password}`,
        },
        body: JSON.stringify({
          band,
          showDate,
          venueName,
          city,
          state,
          setlistText,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: "success", text: `Success: ${data.message}` });
        setShowDate("");
        setVenueName("");
        setCity("");
        setState("");
        setSetlistText("");
        setPreview([]);
      } else {
        setMessage({ type: "error", text: `Error: ${data.error}` });
      }
    } catch (err) {
      setMessage({ type: "error", text: "Failed to submit" });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md space-y-8 py-12">
        <div className="text-center">
          <h1 className="font-headline text-3xl font-bold text-on-surface">Admin Access</h1>
          <p className="mt-2 text-sm text-on-surface-variant">Enter password to continue</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="password" className="sr-only">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div>
        <h1 className="font-headline text-3xl font-bold text-on-surface">Add Setlist</h1>
        <p className="mt-2 text-sm text-on-surface-variant">
          Manually add a show and setlist to the database
        </p>
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

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="band" className="block font-label text-xs font-medium text-on-surface-variant">
              Band
            </label>
            <select
              id="band"
              value={band}
              onChange={(e) => setBand(e.target.value)}
              className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
            >
              {ACTIVE_BANDS.map((b) => (
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
              onChange={(e) => setShowDate(e.target.value)}
              required
              className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
            />
          </div>
        </div>

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
              required
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
              required
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
              required
              placeholder="ST"
              className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none"
            />
          </div>
        </div>

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
            placeholder={`Set 1 Song A, Song B {'>'} Song C, Song D\nSet 2 Song X, Song Y\nEncore Song Z`}
            className="mt-1 w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-on-surface focus:border-primary focus:outline-none font-mono text-sm"
          />
          <p className="mt-1 text-xs text-on-surface-variant">
            Format: "Set 1" or "Encore" followed by comma-separated song names. Use "{'>'}" for segues.
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
                  <span className="w-12 text-on-surface-variant">
                    {row.set === 99 ? "Enc" : `Set ${row.set}`} {row.position}.
                  </span>
                  <span>{row.song}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || preview.length === 0}
          className="w-full rounded-xl bg-primary px-4 py-3 font-label text-sm font-medium text-on-primary transition hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting ? "Submitting..." : "Add Setlist"}
        </button>
      </form>
    </div>
  );
}