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
      className="inline-flex items-center gap-2 rounded-full border border-outline-variant/24 bg-surface/75 px-4 py-2 font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
    >
      <ShareIcon />
      {displayLabel}
    </button>
  );
}
