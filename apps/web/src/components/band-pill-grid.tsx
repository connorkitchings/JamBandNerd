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
          className={`touch-manipulation flex min-h-11 items-center justify-center rounded-full border px-3 py-2 text-center font-headline text-[10px] font-bold uppercase tracking-[0.14rem] transition focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none sm:text-[11px] ${
            item.active
              ? "border-primary/25 bg-primary/12 text-primary"
              : "border-outline-variant/40 bg-surface/75 text-on-surface-variant hover:border-primary/35 hover:text-on-surface"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}
