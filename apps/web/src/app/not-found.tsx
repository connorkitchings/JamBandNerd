import Link from "next/link";

import { bandPath } from "@/lib/band-routes";
import { DEFAULT_BAND_SLUG } from "@/lib/config";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-6xl">
      <div className="editorial-panel border-dashed p-6 md:p-8">
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-accent-text">
          Not found
        </p>
        <h1 className="mt-2 text-2xl font-bold text-on-surface md:text-4xl">
          This page is not available
        </h1>
        <p className="mt-3 max-w-2xl text-base text-on-surface-variant">
          The route may have moved during the single-model V1 cleanup. Head back
          to the live prediction board.
        </p>
        <Link
          href={bandPath(DEFAULT_BAND_SLUG, "predictions")}
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-full bg-accent px-5 py-2 text-sm font-bold text-on-accent transition hover:brightness-95"
        >
          View predictions
        </Link>
      </div>
    </div>
  );
}
