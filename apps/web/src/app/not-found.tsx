import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-6xl">
      <div className="editorial-panel border-dashed p-6 md:p-8">
        <p className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-primary">
          Not found
        </p>
        <h1 className="mt-3 font-headline text-3xl font-semibold uppercase tracking-[-0.03em] text-on-surface">
          This page is not available
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-on-surface-variant">
          The route may have moved during the single-model V1 cleanup. Head back
          to the live prediction board.
        </p>
        <Link
          href="/predictions"
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-full border border-primary/30 bg-primary/12 px-5 py-2.5 font-headline text-xs font-bold uppercase tracking-[0.14rem] text-primary transition hover:border-primary hover:bg-primary/16 focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
        >
          View predictions
        </Link>
      </div>
    </div>
  );
}
