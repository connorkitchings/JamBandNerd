"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { MOBILE_NAV_ITEMS, isActivePath } from "@/lib/navigation";

export function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Mobile navigation"
      className="safe-bottom-nav fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-background/95 px-2 pt-3 backdrop-blur lg:hidden"
    >
      <div className="flex items-center justify-around">
        {MOBILE_NAV_ITEMS.map((item) => {
          const isActive = isActivePath(pathname, item.matches);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex min-w-16 flex-col items-center gap-1 rounded-lg px-3 py-1 text-[10px] uppercase tracking-[0.12rem] transition ${
                isActive ? "text-primary" : "text-on-background/50"
              }`}
            >
              <span className="font-headline text-lg leading-none">{item.icon}</span>
              <span className="font-label">{item.mobileLabel}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
