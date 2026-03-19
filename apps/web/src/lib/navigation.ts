export type NavItem = {
  href: string;
  label: string;
  mobileLabel: string;
  icon: string;
  matches: string[];
};

export const DESKTOP_NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "Predictions",
    mobileLabel: "Predict",
    icon: "◈",
    matches: ["/", "/predictions"],
  },
  {
    href: "/performance",
    label: "Performance",
    mobileLabel: "Stats",
    icon: "◬",
    matches: ["/performance"],
  },
  {
    href: "/explorer",
    label: "Analysis",
    mobileLabel: "Explore",
    icon: "◎",
    matches: ["/explorer", "/compare"],
  },
  {
    href: "/about",
    label: "About",
    mobileLabel: "About",
    icon: "○",
    matches: ["/about"],
  },
];

export const MOBILE_NAV_ITEMS: NavItem[] = [
  {
    href: "/explorer",
    label: "Analysis",
    mobileLabel: "Explore",
    icon: "◎",
    matches: ["/explorer", "/compare"],
  },
  {
    href: "/performance",
    label: "Performance",
    mobileLabel: "Stats",
    icon: "◬",
    matches: ["/performance"],
  },
  {
    href: "/",
    label: "Predictions",
    mobileLabel: "Predict",
    icon: "◈",
    matches: ["/", "/predictions"],
  },
  {
    href: "/last-show",
    label: "Last Show",
    mobileLabel: "Last Show",
    icon: "◧",
    matches: ["/last-show"],
  },
  {
    href: "/about",
    label: "About",
    mobileLabel: "About",
    icon: "○",
    matches: ["/about"],
  },
];

const DETAIL_ROUTE_PREFIXES = ["/last-show"];

export function isActivePath(pathname: string, matches: string[]) {
  return matches.includes(pathname);
}

export function isDetailPath(pathname: string) {
  return DETAIL_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
