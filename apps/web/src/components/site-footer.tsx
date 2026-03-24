import Link from "next/link";
import { SITE_COPYRIGHT_YEAR, SITE_NAME, SITE_VERSION } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-white/10 px-6 py-10 md:px-8 lg:px-10">
      <div className="flex flex-col items-center gap-4 text-center text-xs text-on-surface/40">
        <p>
          © {SITE_COPYRIGHT_YEAR} {SITE_NAME} • v{SITE_VERSION}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-6">
          <Link
            className="underline decoration-dotted transition hover:text-primary"
            href="/about"
          >
            About
          </Link>
          <Link
            className="underline decoration-dotted transition hover:text-primary"
            href="/data-use"
          >
            Data Use
          </Link>
          <Link
            className="underline decoration-dotted transition hover:text-primary"
            href="/contact"
          >
            Contact
          </Link>
        </div>
      </div>
    </footer>
  );
}
