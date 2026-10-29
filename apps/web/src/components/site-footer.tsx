import Link from "next/link";
import { SITE_COPYRIGHT_YEAR, SITE_NAME, SITE_VERSION } from "@/lib/site";

const footerLinkClassName =
  "inline-flex min-h-11 items-center justify-center rounded-md border border-line bg-surface-2 px-4 py-2 text-center text-sm text-on-surface-variant transition hover:text-on-surface";

export function SiteFooter() {
  return (
    <footer className="mt-0 px-4 pb-20 pt-0 md:px-6 md:pb-0 lg:px-8">
      <div className="mx-auto max-w-7xl rounded-xl border border-line bg-surface px-6 py-6 text-center md:px-8">
        <p className="text-sm text-on-surface-variant">
          © {SITE_COPYRIGHT_YEAR} {SITE_NAME} • v{SITE_VERSION}
        </p>
        <p className="mx-auto mt-3 max-w-3xl text-xs leading-5 text-on-surface-variant">
          This site is not affiliated with, or endorsed by, any of the bands or
          management referenced on this site.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2 md:flex md:flex-wrap md:items-center md:justify-center md:gap-3">
          <Link className={footerLinkClassName} href="/about">
            About
          </Link>
          <Link className={footerLinkClassName} href="/data-use">
            Data Use
          </Link>
          <Link className={footerLinkClassName} href="/contact">
            Contact
          </Link>
        </div>
      </div>
    </footer>
  );
}
