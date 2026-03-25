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
    label: "Compare",
    mobileLabel: "Compare",
    icon: "◎",
    matches: ["/compare"],
  },
  {
    href: "/replay",
    label: "Replay",
    mobileLabel: "Replay",
    icon: "◧",
    matches: ["/replay", "/explorer"],
  },
];

export const MOBILE_NAV_ITEMS: NavItem[] = [
  {
    href: "/compare",
    label: "Compare",
    mobileLabel: "Compare",
    icon: "◎",
    matches: ["/compare"],
  },
  {
    href: "/performance",
    label: "Performance",
    mobileLabel: "Stats",
    icon: "◬",
    matches: ["/performance"],
  },
  {
    href: "/replay",
    label: "Replay",
    mobileLabel: "Replay",
    icon: "◧",
    matches: ["/replay", "/explorer"],
  },
  {
    href: "/predictions",
    label: "Predictions",
    mobileLabel: "Predict",
    icon: "◈",
    matches: ["/predictions"],
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
