type NavItem = {
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
    mobileLabel: "Predictions",
    icon: "◈",
    matches: ["/predictions"],
  },
  {
    href: "/performance",
    label: "Performance",
    mobileLabel: "Performance",
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

export const MOBILE_NAV_ITEMS: NavItem[] = DESKTOP_NAV_ITEMS;

export function isActivePath(pathname: string, matches: string[]) {
  return matches.includes(pathname);
}
