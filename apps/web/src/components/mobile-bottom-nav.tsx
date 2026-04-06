"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { MOBILE_NAV_ITEMS, isActivePath } from "@/lib/navigation";

export function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Mobile navigation"
      className="safe-bottom-nav fixed inset-x-0 bottom-0 z-50 backdrop-blur-xl md:hidden"
    >
      <div className="editorial-chip flex w-full items-center justify-between rounded-none border-x-0 border-b-0 border-t border-outline-variant/30 bg-background/92 px-3 py-2 shadow-[0_-10px_30px_rgba(0,0,0,0.22)]">
        {MOBILE_NAV_ITEMS.map((item) => {
          const isActive = isActivePath(pathname, item.matches);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-label={item.mobileLabel}
              className={`touch-manipulation flex min-h-12 flex-1 flex-col items-center justify-center gap-1 rounded-2xl px-2 py-2 text-[10px] uppercase tracking-[0.12rem] transition ${
                isActive
                  ? "bg-primary/12 text-primary shadow-[inset_0_0_0_1px_rgba(255,191,105,0.14)]"
                  : "text-on-background/55 hover:bg-surface/70 hover:text-on-background"
              }`}
            >
              <span className="font-headline text-lg leading-none" aria-hidden="true">
                {item.icon}
              </span>
              <span className="font-label">{item.mobileLabel}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
