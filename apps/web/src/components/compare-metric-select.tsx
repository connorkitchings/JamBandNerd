"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

type CompareMetricSelectProps = {
  selectedMetric: number;
  options: number[];
};

export function CompareMetricSelect({
  selectedMetric,
  options,
}: CompareMetricSelectProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startNavigation] = useTransition();

  function handleChange(nextMetric: string) {
    if (!nextMetric) {
      return;
    }

    const params = new URLSearchParams(searchParams.toString());
    params.set("k", nextMetric);

    startNavigation(() => {
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
    });
  }

  return (
    <div className="md:ml-auto md:w-[11rem]">
      <select
        id="compare-metric-select"
        value={String(selectedMetric)}
        onChange={(event) => handleChange(event.target.value)}
        disabled={isPending}
        className="touch-manipulation min-h-11 w-full rounded-xl border border-outline-variant/20 bg-surface px-4 py-3 text-right font-headline text-sm text-on-surface outline-none transition focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-wait disabled:opacity-70"
        aria-label="Select comparison metric"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            Top {option}
          </option>
        ))}
      </select>
    </div>
  );
}
