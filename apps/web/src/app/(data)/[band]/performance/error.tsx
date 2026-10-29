"use client";

import { useEffect } from "react";

type Props = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function Error({ error, reset }: Props) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="editorial-panel p-6 md:p-8">
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-accent-text">
          Page error
        </p>
        <h1 className="mt-2 text-2xl font-bold text-on-surface">
          Something interrupted this view
        </h1>
        <p className="mt-3 max-w-2xl text-base text-on-surface-variant">
          The performance page failed while loading its latest data. Retry the
          request, or return to the prediction board from the site navigation.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-full bg-accent px-5 text-sm font-bold text-on-accent transition hover:opacity-90"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
