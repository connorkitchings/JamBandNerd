"use client";

import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { formatCompactDateLabel } from "@/lib/format";

type Props = {
  band: string;
  selectedDate: string;
  options: Array<{
    showDate: string;
  }>;
};

export function ReplayShowSelect({ band, selectedDate, options }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  return (
    <label className="flex flex-col gap-2">
      <span className="font-label text-[10px] font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
        Select show
      </span>
      <select
        aria-label="Select replay show"
        className="min-h-12 w-full rounded-xl border border-outline-variant/30 bg-surface px-4 py-3 font-headline text-sm text-on-surface outline-none transition focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-wait disabled:opacity-70"
        disabled={isPending}
        value={selectedDate}
        onChange={(event) => {
          const nextDate = event.target.value;
          if (!nextDate || nextDate === selectedDate) {
            return;
          }

          startTransition(() => {
            router.push(`${pathname}?band=${band}&date=${nextDate}`, {
              scroll: false,
            });
          });
        }}
      >
        {options.map((option) => (
          <option key={option.showDate} value={option.showDate}>
            {formatCompactDateLabel(option.showDate)}
          </option>
        ))}
      </select>
    </label>
  );
}
