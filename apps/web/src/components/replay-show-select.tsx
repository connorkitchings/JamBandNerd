"use client";

import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { formatCompactDateLabel } from "@/lib/format";

type ReplayShowSelectProps = {
  band: string;
  selectedDate: string | null;
  options: Array<{
    showDate: string;
  }>;
  label?: string;
};

export function ReplayShowSelect({
  band,
  selectedDate,
  options,
  label,
}: ReplayShowSelectProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startNavigation] = useTransition();
  const currentValue = selectedDate ?? options[0]?.showDate ?? "";

  function handleChange(nextDate: string) {
    if (!nextDate) {
      return;
    }

    startNavigation(() => {
      router.push(`${pathname}?band=${band}&date=${nextDate}`, { scroll: false });
    });
  }

  return (
    <div className="space-y-2">
      {label ? (
        <p className="font-label text-[10px] uppercase tracking-[0.16em] text-on-surface-variant">
          {label}
        </p>
      ) : null}
      <select
        id="replay-show-select"
        value={currentValue}
        onChange={(event) => handleChange(event.target.value)}
        disabled={isPending}
        className="touch-manipulation min-h-11 w-full rounded-xl border border-outline-variant/20 bg-surface px-4 py-3 font-headline text-sm text-on-surface outline-none transition focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-wait disabled:opacity-70"
        aria-label="Select replay show"
      >
        {options.map((option) => (
          <option key={option.showDate} value={option.showDate}>
            {formatCompactDateLabel(option.showDate)}
          </option>
        ))}
      </select>
    </div>
  );
}
