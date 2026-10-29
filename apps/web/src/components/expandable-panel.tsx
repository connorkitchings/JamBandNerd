import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  collapseLabel?: string;
  expandLabel?: string;
  bodyClassName?: string;
  buttonClassName?: string;
  containerClassName?: string;
};

/** Native disclosure: no client state, keyboard and screen-reader support come from `<details>`. */
export function ExpandablePanel({
  children,
  collapseLabel = "Collapse",
  expandLabel = "Expand",
  bodyClassName = "",
  buttonClassName = "",
  containerClassName = "",
}: Props) {
  return (
    <details className={`group ${containerClassName}`}>
      <summary
        className={`flex min-h-11 cursor-pointer list-none items-center justify-center [&::-webkit-details-marker]:hidden ${buttonClassName}`}
      >
        <span className="group-open:hidden">{expandLabel}</span>
        <span className="hidden group-open:inline">{collapseLabel}</span>
      </summary>
      <div className={bodyClassName}>{children}</div>
    </details>
  );
}
