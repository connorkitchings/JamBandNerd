"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { DESKTOP_NAV_ITEMS, isActivePath, isDetailPath } from "@/lib/navigation";
import { SITE_NAME } from "@/lib/site";

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
      <div className="editorial-chip relative mx-auto max-w-7xl rounded-full px-3 py-2 md:px-4 md:py-3">
        <div className="flex items-center md:hidden">
          <div className="flex w-12 items-center">
            {showMobileBackButton ? (
              <button
                aria-label="Go back"
                className="flex size-10 items-center justify-center rounded-full border border-outline-variant/20 bg-surface/70 text-on-background transition hover:border-primary/40 hover:text-primary"
                onClick={handleBack}
                type="button"
              >
                <BackIcon />
              </button>
            ) : (
              <div className="size-10" />
            )}
          </div>

          <Link
            href="/"
            className="absolute inset-y-0 left-12 right-12 flex items-center justify-center gap-2 font-headline font-bold tracking-[-0.1em] text-on-background"
          >
            <Image
              src="/logo.png"
              alt="JamBandNerd"
              width={34}
              height={34}
              className="size-8 shrink-0 rounded-full ring-1 ring-white/10 min-[380px]:size-9"
            />
            <span className="truncate text-center text-[clamp(1.3rem,6vw,1.9rem)] leading-none">
              {SITE_NAME}
            </span>
          </Link>
        </div>

        <div className="hidden min-w-0 items-center justify-between gap-6 md:flex">
          <Link
            href="/"
            className="flex shrink-0 items-center gap-3 font-headline font-bold uppercase tracking-[-0.06em] text-on-background"
          >
            <Image
              src="/logo.png"
              alt="JamBandNerd Logo"
              width={42}
              height={42}
              className="rounded-full ring-1 ring-white/10"
            />
            <span className="text-[1.65rem] leading-none">{SITE_NAME}</span>
          </Link>

          <div className="min-w-0 flex-1 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <div className="flex min-w-max items-center justify-end gap-2">
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
          </div>
        </div>
      </div>
    </nav>
  );
}
