"use client";

import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { formatMMDDYYYY } from "@/lib/format";

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
      <span className="text-center font-label text-[10px] font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
        Select show
      </span>
      <select
        className="min-h-14 w-full rounded-xl border border-outline-variant/30 bg-surface px-4 py-3 text-center font-headline text-base font-semibold text-primary outline-none transition focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-wait disabled:opacity-70"
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
            {formatMMDDYYYY(option.showDate)}
          </option>
        ))}
      </select>
    </label>
  );
}
