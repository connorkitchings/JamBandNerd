"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Predict", icon: "◈", matches: ["/", "/predictions"] },
  { href: "/explorer", label: "Explore", icon: "◎", matches: ["/explorer", "/compare"] },
  { href: "/performance", label: "Stats", icon: "◬", matches: ["/performance"] },
  { href: "/about", label: "About", icon: "○", matches: ["/about", "/last-show"] },
];

export function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-background/95 px-2 py-3 backdrop-blur lg:hidden">
      <div className="flex items-center justify-around">
        {items.map((item) => {
          const isActive = item.matches.includes(pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex min-w-16 flex-col items-center gap-1 rounded-lg px-3 py-1 text-[10px] uppercase tracking-[0.12rem] transition ${
                isActive ? "text-primary" : "text-on-background/50"
              }`}
            >
              <span className="font-headline text-lg leading-none">{item.icon}</span>
              <span className="font-label">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
