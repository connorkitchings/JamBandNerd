"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { bandPath } from "@/lib/band-routes";
import { formatMMDDYYYY } from "@/lib/format";

type Props = {
  band: string;
  selectedDate: string;
  options: Array<{
    showDate: string;
  }>;
};

export function ReplayShowSelect({ band, selectedDate, options }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
        Select show
      </span>
      <select
        className="min-h-11 w-full min-w-[220px] rounded-md border border-line bg-surface-2 px-3 py-2 text-sm font-semibold text-on-surface disabled:cursor-wait disabled:opacity-70"
        disabled={isPending}
        value={selectedDate}
        onChange={(event) => {
          const nextDate = event.target.value;
          if (!nextDate || nextDate === selectedDate) {
            return;
          }

          startTransition(() => {
            router.push(bandPath(band, "replay", nextDate), {
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
