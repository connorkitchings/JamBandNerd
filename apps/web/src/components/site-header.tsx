"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { DESKTOP_NAV_ITEMS, isActivePath, isDetailPath } from "@/lib/navigation";

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

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const showMobileBackButton = isDetailPath(pathname);

  function handleBack() {
    if (window.history.length > 1) {
      router.back();
      return;
    }

    router.push("/predictions");
  }

  return (
    <nav
      aria-label="Primary navigation"
      className="fixed inset-x-0 top-0 z-50 border-b border-outline-variant/20 bg-background/80 px-4 py-4 backdrop-blur-xl md:px-6"
    >
      <div className="editorial-chip relative mx-auto flex max-w-7xl items-center justify-between gap-4 rounded-full px-3 py-2 md:px-4">
        <div className="flex w-12 items-center md:w-auto">
          {showMobileBackButton ? (
            <button
              aria-label="Go back"
              className="flex size-10 items-center justify-center rounded-full border border-outline-variant/20 bg-surface/70 text-on-background transition hover:border-primary/40 hover:text-primary md:hidden"
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
            className="hidden items-center gap-3 font-headline text-xl font-bold uppercase tracking-[-0.06em] text-on-background md:flex"
          >
            <Image
              src="/logo.png"
              alt="JamBandNerd Logo"
              width={34}
              height={34}
              className="rounded-full ring-1 ring-white/10"
            />
            <span>JamBandNerd</span>
          </Link>
        </div>

        <Link
          href="/"
          className="absolute left-1/2 flex -translate-x-1/2 items-center gap-2 font-headline text-xl font-bold uppercase tracking-[-0.06em] text-on-background md:hidden"
        >
          <Image
            src="/logo.png"
            alt="JamBandNerd"
            width={28}
            height={28}
            className="rounded-full ring-1 ring-white/10"
          />
          JBN
        </Link>

        <div className="hidden items-center gap-2 md:flex">
          {DESKTOP_NAV_ITEMS.map((link) => {
            const isActive = isActivePath(pathname, link.matches);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-full px-4 py-2 font-headline text-xs uppercase tracking-[0.16rem] transition duration-200 ${
                  isActive
                    ? "border border-primary/25 bg-primary/12 text-primary shadow-[0_0_0_1px_rgba(255,191,105,0.08)]"
                    : "border border-transparent text-on-background/70 hover:border-outline-variant/25 hover:bg-surface/60 hover:text-on-background"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        <div className="w-12 md:w-[180px]" aria-hidden="true" />
      </div>
    </nav>
  );
}
