"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { buildNavLinks } from "@/lib/navigation";
import { useCurrentBand } from "@/lib/use-current-band";

export function MobileBottomNav() {
  const pathname = usePathname();
  const navLinks = buildNavLinks(useCurrentBand(), pathname);

  return (
    <nav
      aria-label="Mobile navigation"
      className="safe-bottom-nav fixed inset-x-0 bottom-0 z-50 border-t border-line bg-background md:hidden"
    >
      <div className="flex w-full items-center justify-between gap-1 px-2 py-2">
        {navLinks.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-label={item.mobileLabel}
            aria-current={item.active ? "page" : undefined}
            className={`touch-manipulation flex min-h-12 flex-1 flex-col items-center justify-center gap-1 rounded-md px-1 py-1 text-xs font-bold transition ${
              item.active
                ? "bg-surface-2 text-on-surface shadow-[inset_0_-2px_0_var(--accent)]"
                : "text-on-surface-variant hover:bg-surface-2 hover:text-on-surface"
            }`}
          >
            <span className="font-headline text-lg leading-none" aria-hidden="true">
              {item.icon}
            </span>
            <span>{item.mobileLabel}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
