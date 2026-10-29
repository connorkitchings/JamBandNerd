import Link from "next/link";

export type BandPillLink = {
  href: string;
  label: string;
  active: boolean;
};

type Props = {
  links: BandPillLink[];
  className?: string;
};

export function BandPillGrid({ links, className = "" }: Props) {
  return (
    <div className={`grid auto-rows-fr gap-2 ${className}`}>
      {links.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-current={item.active ? "page" : undefined}
          className={`touch-manipulation flex min-h-11 items-center justify-center rounded-full border px-4 py-2 text-center text-sm font-semibold transition ${
            item.active
              ? "border-accent bg-accent text-on-accent"
              : "border-line bg-surface text-on-surface hover:bg-surface-2"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}
