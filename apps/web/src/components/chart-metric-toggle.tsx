"use client";

export type ChartMetric = "coverage" | "hits";

type Props = {
  currentMetric: ChartMetric;
  onChange: (metric: ChartMetric) => void;
};

const metricOptions: Array<{ value: ChartMetric; label: string }> = [
  { value: "coverage", label: "Coverage" },
  { value: "hits", label: "Hits" },
];

export function ChartMetricToggle({ currentMetric, onChange: setMetric }: Props) {
  return (
    <>
      <select
        aria-label="Chart measure"
        className="min-h-11 w-full rounded-md border border-line bg-surface-2 px-3 text-sm font-semibold text-on-surface md:hidden"
        onChange={(event) => setMetric(event.target.value as ChartMetric)}
        value={currentMetric}
      >
        {metricOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <div
        aria-label="Chart measure"
        className="hidden gap-1 rounded-md border border-line bg-surface-2 p-1 md:inline-flex"
        role="group"
      >
        {metricOptions.map((option) => (
          <button
            key={option.value}
            aria-pressed={currentMetric === option.value}
            className={`touch-manipulation min-h-11 rounded-md px-4 text-sm font-semibold transition-colors ${
              currentMetric === option.value
                ? "bg-accent text-on-accent"
                : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
            }`}
            onClick={() => setMetric(option.value)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
    </>
  );
}
