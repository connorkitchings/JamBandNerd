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
        className="inline-flex min-h-12 items-center justify-center rounded-full border border-primary/30 bg-primary/12 px-5 py-3 text-center font-headline text-base font-medium text-primary transition hover:border-primary hover:bg-primary/16"
      >
        {email}
      </a>
      <button
        type="button"
        onClick={handleCopy}
        className="inline-flex min-h-12 items-center justify-center rounded-full border border-outline-variant/24 bg-surface/75 px-5 py-3 text-center font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
      >
        {copyLabel}
      </button>
    </div>
  );
}
