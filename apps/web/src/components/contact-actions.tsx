"use client";

import { useState } from "react";

type Props = {
  email: string;
};

export function ContactActions({ email }: Props) {
  const [copyLabel, setCopyLabel] = useState("Copy Email");

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(email);
      setCopyLabel("Copied");
      window.setTimeout(() => setCopyLabel("Copy Email"), 1600);
    } catch {
      setCopyLabel("Copy Failed");
      window.setTimeout(() => setCopyLabel("Copy Email"), 1600);
    }
  }

  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
      <a
        href={`mailto:${email}`}
        aria-label={`Email ${email}`}
        className="inline-flex min-h-11 items-center justify-center rounded-full bg-accent px-5 py-2 text-sm font-bold text-on-accent transition hover:brightness-95 text-center"
      >
        {email}
      </a>
      <button
        type="button"
        onClick={handleCopy}
        className="inline-flex min-h-11 items-center justify-center rounded-full border border-line bg-surface px-5 py-2 text-center text-sm font-bold text-on-surface transition hover:bg-surface-2"
      >
        {copyLabel}
      </button>
    </div>
  );
}
