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
    label: "Home",
    mobileLabel: "Home",
    icon: "◉",
    matches: ["/"],
  },
  {
    href: "/predictions",
    label: "Predictions",
    mobileLabel: "Predict",
    icon: "◈",
    matches: ["/predictions"],
  },
  {
    href: "/performance",
    label: "Performance",
    mobileLabel: "Stats",
    icon: "◬",
    matches: ["/performance"],
  },
  {
    href: "/compare",
    label: "Deep-Dive",
    mobileLabel: "Deep-Dive",
    icon: "◎",
    matches: ["/explorer", "/compare"],
  },
];

export const MOBILE_NAV_ITEMS: NavItem[] = [
  {
    href: "/compare",
    label: "Deep-Dive",
    mobileLabel: "Deep-Dive",
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
    href: "/predictions",
    label: "Predictions",
    mobileLabel: "Predict",
    icon: "◈",
    matches: ["/predictions"],
  },
  {
    href: "/last-show",
    label: "Last Show",
    mobileLabel: "Last Show",
    icon: "◧",
    matches: ["/last-show"],
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
