import { bandPath, type BandPage } from "./band-routes.ts";
import type { BandSlug } from "./config.ts";

type NavItem = {
  page: BandPage;
  label: string;
  mobileLabel: string;
  icon: string;
};

export const NAV_ITEMS: NavItem[] = [
  { page: "overview", label: "Home", mobileLabel: "Home", icon: "◉" },
  { page: "predictions", label: "Predictions", mobileLabel: "Predictions", icon: "◈" },
  { page: "performance", label: "Performance", mobileLabel: "Performance", icon: "◬" },
  { page: "replay", label: "Replay", mobileLabel: "Replay", icon: "◎" },
];

export type NavLink = NavItem & { href: string; active: boolean };

/** Nav links for a band, with the one matching `pathname` marked active. */
export function buildNavLinks(band: BandSlug, pathname: string): NavLink[] {
  return NAV_ITEMS.map((item) => {
    const href = bandPath(band, item.page);
    return { ...item, href, active: isActivePath(pathname, href, item.page === "overview") };
  });
}

/** The overview link matches exactly; other links also match their sub-paths (e.g. a replay date). */
export function isActivePath(pathname: string, href: string, exact = false) {
  return pathname === href || (!exact && pathname.startsWith(`${href}/`));
}
