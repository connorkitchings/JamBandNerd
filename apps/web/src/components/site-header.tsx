"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { GlobalSearch, type GlobalSearchItem } from "@/components/global-search";
import { DESKTOP_NAV_ITEMS, isActivePath, isDetailPath } from "@/lib/navigation";

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

function BackIcon() {
  return (
    <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 24 24">
      <path
        d="M15 5L8 12L15 19"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

type Props = {
  searchItems: GlobalSearchItem[];
};

export function SiteHeader({ searchItems }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const showMobileBackButton = isDetailPath(pathname);

  function handleBack() {
    if (window.history.length > 1) {
      router.back();
      return;
    }

    router.push("/");
  }

  return (
    <nav
      aria-label="Primary navigation"
      className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-background/95 px-6 py-4 backdrop-blur"
    >
      <div className="relative flex items-center justify-between gap-4">
        <div className="flex w-12 items-center md:w-auto">
          {showMobileBackButton ? (
            <button
              aria-label="Go back"
              className="flex size-10 items-center justify-center rounded-full text-on-background transition-colors hover:text-primary md:hidden"
              onClick={handleBack}
              type="button"
            >
              <BackIcon />
            </button>
          ) : (
            <div className="size-10 md:hidden" />
          )}
          <Link
            href="/"
            className="hidden font-headline text-2xl font-bold tracking-[-0.08em] text-on-background md:block"
          >
            JamBandNerd
          </Link>
        </div>

        <Link
          href="/"
          className="absolute left-1/2 -translate-x-1/2 font-headline text-2xl font-bold tracking-[-0.08em] text-on-background md:hidden"
        >
          JamBandNerd
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {DESKTOP_NAV_ITEMS.map((link) => {
            const isActive = isActivePath(pathname, link.matches);
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

        <div className="flex w-12 items-center justify-end text-on-background md:w-auto md:gap-4">
          <GlobalSearch items={searchItems} />
          
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
