"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  {
    href: "/",
    label: "Predictions",
    matches: ["/", "/predictions"],
  },
  {
    href: "/performance",
    label: "Performance",
    matches: ["/performance"],
  },
  {
    href: "/explorer",
    label: "Analysis",
    matches: ["/explorer", "/compare", "/last-show"],
  },
  {
    href: "/about",
    label: "About",
    matches: ["/about"],
  },
];

function SearchIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M16 16L21 21" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="8" r="3.25" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M5.5 19.5C6.4 16.8 8.76 15 12 15s5.6 1.8 6.5 4.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <circle cx="12" cy="12" r="9.25" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <nav className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-background/95 px-6 py-4 backdrop-blur">
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/"
          className="font-headline text-2xl font-bold tracking-[-0.08em] text-on-background"
        >
          JamBandNerd
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {links.map((link) => {
            const isActive = link.matches.includes(pathname);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`font-headline text-sm uppercase tracking-[0.05rem] transition-colors duration-200 ${
                  isActive
                    ? "border-b-2 border-primary-container pb-1 text-primary-container"
                    : "text-on-background/60 hover:text-on-background"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-4 text-on-background">
          <button
            aria-label="Search"
            className="text-on-background/60 transition-colors hover:text-primary"
            type="button"
          >
            <SearchIcon />
          </button>
          <button
            aria-label="Account"
            className="text-on-background transition-colors hover:text-primary"
            type="button"
          >
            <UserIcon />
          </button>
        </div>
      </div>
    </nav>
  );
}
