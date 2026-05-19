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
      <div className="editorial-panel border-dashed p-6 md:p-8">
        <p className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-primary">
          Page error
        </p>
        <h1 className="mt-3 font-headline text-3xl font-semibold uppercase tracking-[-0.03em] text-on-surface">
          Something interrupted this view
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-on-surface-variant">
          The page failed while loading its latest data. Retry the request, or
          return to the prediction board from the site navigation.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-full border border-primary/30 bg-primary/12 px-5 py-2.5 font-headline text-xs font-bold uppercase tracking-[0.14rem] text-primary transition hover:border-primary hover:bg-primary/16 focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
