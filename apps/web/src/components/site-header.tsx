"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { buildNavLinks } from "@/lib/navigation";
import { SITE_NAME } from "@/lib/site";
import { useCurrentBand } from "@/lib/use-current-band";

export function SiteHeader() {
  const pathname = usePathname();
  const band = useCurrentBand();
  const navLinks = buildNavLinks(band, pathname);

  return (
    <nav
      aria-label="Primary navigation"
      className="fixed inset-x-0 top-0 z-50 border-b border-line bg-background px-4 py-3 md:px-6"
    >
      <div className="relative mx-auto max-w-7xl">
        <div className="flex items-center justify-between md:hidden">
          <div className="size-11" />

          <Link
            href={`/${band}`}
            className="absolute inset-y-0 left-12 right-12 flex items-center justify-center gap-2 rounded-md font-headline font-bold text-on-background"
          >
            <Image
              src="/logo.png"
              alt="JamBandNerd"
              width={34}
              height={34}
              className="size-8 shrink-0 rounded-full"
            />
            <span className="truncate text-center text-xl leading-none">{SITE_NAME}</span>
          </Link>

          <ThemeToggle />
        </div>

        <div className="hidden min-w-0 items-center justify-between gap-6 md:flex">
          <Link
            href={`/${band}`}
            className="flex shrink-0 items-center gap-3 rounded-md font-headline font-bold text-on-background"
          >
            <Image
              src="/logo.png"
              alt="JamBandNerd Logo"
              width={40}
              height={40}
              className="size-10 rounded-full"
            />
            <span className="text-xl leading-none">{SITE_NAME}</span>
          </Link>

          <div className="flex min-w-0 items-center gap-2">
            <div className="min-w-0 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <div className="flex min-w-max items-center justify-end gap-1">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    aria-current={link.active ? "page" : undefined}
                    className={`inline-flex h-11 items-center justify-center rounded-md px-4 text-sm font-bold transition ${
                      link.active
                        ? "bg-surface-2 text-on-surface shadow-[inset_0_-2px_0_var(--accent)]"
                        : "text-on-surface-variant hover:bg-surface-2 hover:text-on-surface"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}
