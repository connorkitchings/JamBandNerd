import Link from "next/link";
import { SITE_COPYRIGHT_YEAR, SITE_NAME, SITE_VERSION } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-0 px-4 pb-20 pt-0 md:px-6 md:pb-0 lg:px-8">
      <div className="mx-auto max-w-7xl rounded-[1.6rem] border border-outline-variant/28 bg-surface-container px-6 py-6 text-center shadow-[0_-1px_0_rgba(255,255,255,0.03),0_28px_72px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.03)] md:px-8">
        <p className="text-xs text-on-surface/55">
          © {SITE_COPYRIGHT_YEAR} {SITE_NAME} • v{SITE_VERSION}
        </p>
        <p className="mx-auto mt-3 max-w-3xl text-[11px] leading-5 text-on-surface-variant/80">
          This site is not affiliated with, or endorsed by, any of the bands or
          management referenced on this site.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2 md:flex md:flex-wrap md:items-center md:justify-center md:gap-3">
          <Link
            className="rounded-full border border-outline-variant/20 px-4 py-2 text-center text-xs transition hover:border-primary/40 hover:text-primary"
            href="/about"
          >
            About
          </Link>
          <Link
            className="rounded-full border border-outline-variant/20 px-4 py-2 text-center text-xs transition hover:border-primary/40 hover:text-primary"
            href="/data-use"
          >
            Data Use
          </Link>
          <Link
            className="rounded-full border border-outline-variant/20 px-4 py-2 text-center text-xs transition hover:border-primary/40 hover:text-primary"
            href="/contact"
          >
            Contact
          </Link>
          <Link
            className="rounded-full border border-outline-variant/20 px-4 py-2 text-center text-xs transition hover:border-primary/40 hover:text-primary"
            href="/admin/setlist"
          >
            Admin
          </Link>
        </div>
      </div>
    </footer>
  );
}
