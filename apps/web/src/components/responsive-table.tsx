import type { ReactNode } from "react";

type ResponsiveTableFrameProps = {
  children: ReactNode;
  minWidthClassName: string;
  tableClassName?: string;
  testId?: string;
};

export const TABLE_HEAD_CLASS =
  "px-3 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant sm:px-4";
export const TABLE_CELL_CLASS = "px-3 py-3 sm:px-4 sm:py-4";

export function ResponsiveTableFrame({
  children,
  minWidthClassName,
  tableClassName,
  testId,
}: ResponsiveTableFrameProps) {
  return (
    <div
      className="overflow-x-auto rounded-xl border border-outline-variant/30 [scrollbar-gutter:stable] [-webkit-overflow-scrolling:touch]"
      data-testid={testId ? `${testId}-frame` : undefined}
    >
      <table
        className={`w-full border-collapse text-left text-sm ${minWidthClassName} ${
          tableClassName ?? ""
        }`}
        data-testid={testId ? `${testId}-table` : undefined}
      >
        {children}
      </table>
    </div>
  );
}
