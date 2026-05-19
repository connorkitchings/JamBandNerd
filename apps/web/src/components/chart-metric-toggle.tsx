"use client";

import { useRouter, useSearchParams } from "next/navigation";

export type ChartMetric = "coverage" | "hits";

type Props = {
  currentMetric: ChartMetric;
};

const metricOptions: Array<{ value: ChartMetric; label: string }> = [
  { value: "coverage", label: "Coverage" },
  { value: "hits", label: "Hits" },
];

export function ChartMetricToggle({ currentMetric }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function setMetric(metric: ChartMetric) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("metric", metric);
    router.push(`?${params}`, { scroll: false });
  }

  return (
    <>
      <select
        aria-label="Chart measure"
        className="h-10 w-full rounded-xl border border-outline-variant/20 bg-surface/55 px-3 font-label text-[10px] uppercase tracking-wider text-on-surface focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none md:hidden"
        onChange={(event) => setMetric(event.target.value as ChartMetric)}
        value={currentMetric}
      >
        {metricOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <div className="hidden rounded-xl border border-outline-variant/15 bg-surface/45 p-1 md:inline-flex">
        {metricOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setMetric(option.value)}
            className={`touch-manipulation min-h-9 rounded-lg px-3 py-1.5 font-label text-[10px] uppercase tracking-wider transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none ${
              currentMetric === option.value
                ? "bg-primary/18 text-primary ring-1 ring-primary/35"
                : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
            }`}
            aria-pressed={currentMetric === option.value}
          >
            {option.label}
          </button>
        ))}
      </div>
    </>
  );
}
