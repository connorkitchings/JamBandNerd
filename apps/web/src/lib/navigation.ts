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
    mobileLabel: "Model",
    icon: "◬",
    matches: ["/performance"],
  },
  {
    href: "/replay",
    label: "Replay",
    mobileLabel: "Replay",
    icon: "◎",
    matches: ["/replay"],
  },
];

export const MOBILE_NAV_ITEMS: NavItem[] = [
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
    href: "/replay",
    label: "Replay",
    mobileLabel: "Replay",
    icon: "◎",
    matches: ["/replay"],
  },
  {
    href: "/performance",
    label: "Performance",
    mobileLabel: "Model",
    icon: "◬",
    matches: ["/performance"],
  },
];

const DETAIL_ROUTE_PREFIXES = ["/last-show", "/replay"];

export function isActivePath(pathname: string, matches: string[]) {
  return matches.includes(pathname);
}

export function isDetailPath(pathname: string) {
  return DETAIL_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
