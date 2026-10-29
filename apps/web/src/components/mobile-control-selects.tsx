"use client";

import { useRouter } from "next/navigation";
import { useId, useTransition } from "react";

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
  const baseId = useId();

  return (
    <div className="grid gap-3 min-[430px]:grid-cols-2 md:hidden">
      {groups.map((group) => {
        const selectedHref = group.options.find((option) => option.active)?.href ?? group.options[0]?.href ?? "";
        const selectId = `${baseId}-${group.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

        return (
          <div key={group.label} className="flex flex-col gap-1.5">
            <label
              htmlFor={selectId}
              className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant"
            >
              {group.label}
            </label>
            <div className="relative">
              <select
                id={selectId}
                className="min-h-11 w-full appearance-none rounded-md border border-line bg-surface-2 px-3 py-2 pr-10 text-sm font-semibold text-on-surface disabled:cursor-wait disabled:opacity-70"
                data-testid={group.testId}
                value={selectedHref}
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
                className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-on-surface-variant"
              >
                ▾
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
