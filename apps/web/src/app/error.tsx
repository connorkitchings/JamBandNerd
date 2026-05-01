"use client";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 px-4 text-center">
      <h2 className="text-2xl font-semibold text-on-surface">Something went wrong</h2>
      <p className="text-on-surface-variant max-w-md">
        An unexpected error occurred while loading this page.
      </p>
      <button
        onClick={() => reset()}
        className="mt-2 px-6 py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-hover transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
