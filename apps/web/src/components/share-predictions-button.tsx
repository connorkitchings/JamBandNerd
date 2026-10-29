"use client";

import { useState } from "react";

type Props = {
  text: string;
  label?: string;
};

function ShareIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M4 12C4 12 5.5 6 12 6C18.5 6 20 12 20 12"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="M4 12C4 12 5.5 18 12 18C18.5 18 20 12 20 12"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="M12 4V20M12 4L8 8M12 4L16 8"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

export function SharePredictionsButton({ text, label = "Share" }: Props) {
  const [status, setStatus] = useState<"idle" | "shared" | "copied" | "failed">("idle");

  async function handleShare() {
    try {
      if (typeof navigator.share === "function") {
        await navigator.share({ text });
        setStatus("shared");
      } else if (typeof navigator.clipboard === "object") {
        await navigator.clipboard.writeText(text);
        setStatus("copied");
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        setStatus("copied");
      } catch {
        setStatus("failed");
      }
    }

    window.setTimeout(() => setStatus("idle"), 1600);
  }

  const displayLabel =
    status === "shared"
      ? "Shared"
      : status === "copied"
        ? "Copied"
        : status === "failed"
          ? "Failed"
          : label;

  return (
    <button
      type="button"
      onClick={handleShare}
      aria-live="polite"
      className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line bg-surface px-4 text-sm font-semibold text-on-surface transition hover:bg-surface-container"
    >
      <ShareIcon />
      {displayLabel}
    </button>
  );
}
