import type { ReactNode } from "react";

type ResponsiveTableFrameProps = {
  children: ReactNode;
  /** Accessible table name, announced by screen readers (visually hidden). */
  caption: string;
  minWidthClassName: string;
  tableClassName?: string;
  testId?: string;
};

export const TABLE_HEAD_CLASS =
  "border-b border-line px-3 py-2.5 text-left text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant";
export const TABLE_CELL_CLASS = "border-b border-line px-3 py-2.5 tabular-nums";
/** Row header cell: reads as a normal cell but is announced as the row's label. */
export const TABLE_ROW_HEAD_CLASS = `${TABLE_CELL_CLASS} text-left font-semibold text-on-surface`;

/** Text plus a filled dot (yes) or ring (no), so state never relies on color alone. */
export function StatusMark({ on, onLabel, offLabel }: { on: boolean; onLabel: string; offLabel: string }) {
  return on ? (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-bold text-teal">
      <span aria-hidden="true" className="size-2 rounded-full bg-teal" />
      {onLabel}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-bold text-on-surface-variant">
      <span aria-hidden="true" className="size-2 rounded-full border-2 border-on-surface-variant" />
      {offLabel}
    </span>
  );
}

export function ResponsiveTableFrame({
  children,
  caption,
  minWidthClassName,
  tableClassName,
  testId,
}: ResponsiveTableFrameProps) {
  return (
    <div
      className="horizontal-scroll-surface rounded-xl border border-line bg-surface"
      data-testid={testId ? `${testId}-frame` : undefined}
    >
      <table
        className={`w-full border-collapse text-left text-sm ${minWidthClassName} ${
          tableClassName ?? ""
        }`}
        data-testid={testId ? `${testId}-table` : undefined}
      >
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}
