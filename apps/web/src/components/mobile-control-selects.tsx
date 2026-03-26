"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

type MobileControlOption = {
  href: string;
  label: string;
  active: boolean;
};

type MobileControlGroup = {
  label: string;
  options: MobileControlOption[];
  testId?: string;
};

type Props = {
  groups: MobileControlGroup[];
};

export function MobileControlSelects({ groups }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  return (
    <div className="editorial-chip grid gap-3 rounded-[1.35rem] p-3 min-[430px]:grid-cols-2 md:hidden">
      {groups.map((group) => {
        const selectedHref = group.options.find((option) => option.active)?.href ?? group.options[0]?.href ?? "";

        return (
          <label key={group.label} className="flex flex-col gap-2">
            <span className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
              {group.label}
            </span>
            <div className="relative">
              <select
                aria-label={group.label}
                className="min-h-12 w-full appearance-none rounded-2xl border border-outline-variant/35 bg-surface/80 px-4 py-3 pr-11 text-sm text-on-surface outline-none transition focus:border-primary/45 focus:bg-surface-container"
                data-testid={group.testId}
                defaultValue={selectedHref}
                disabled={isPending || group.options.length === 0}
                onChange={(event) => {
                  const nextHref = event.target.value;
                  if (!nextHref || nextHref === selectedHref) {
                    return;
                  }

                  startTransition(() => {
                    router.push(nextHref, { scroll: false });
                  });
                }}
              >
                {group.options.map((option) => (
                  <option key={option.href} value={option.href}>
                    {option.label}
                  </option>
                ))}
              </select>
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-on-surface-variant"
              >
                ▾
              </span>
            </div>
          </label>
        );
      })}
    </div>
  );
}
