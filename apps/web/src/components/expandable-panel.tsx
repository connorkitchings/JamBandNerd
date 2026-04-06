"use client";

import { useState } from "react";
import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  collapseLabel?: string;
  expandLabel?: string;
  bodyClassName?: string;
  buttonClassName?: string;
  containerClassName?: string;
};

export function ExpandablePanel({
  children,
  collapseLabel = "Collapse",
  expandLabel = "Expand",
  bodyClassName = "",
  buttonClassName = "",
  containerClassName = "",
}: Props) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!isExpanded) {
    return (
      <div className={containerClassName}>
        <button
          type="button"
          className={buttonClassName}
          onClick={() => setIsExpanded(true)}
        >
          {expandLabel}
        </button>
      </div>
    );
  }

  return (
    <div className={containerClassName}>
      <div className={bodyClassName}>{children}</div>
      <div className="px-3 pb-3 pt-1">
        <button
          type="button"
          className={buttonClassName}
          onClick={() => setIsExpanded(false)}
        >
          {collapseLabel}
        </button>
      </div>
    </div>
  );
}
