"use client";

import { useId, useState } from "react";
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
  const bodyId = useId();

  if (!isExpanded) {
    return (
      <div className={containerClassName}>
        <button
          type="button"
          className={buttonClassName}
          aria-controls={bodyId}
          aria-expanded={false}
          onClick={() => setIsExpanded(true)}
        >
          {expandLabel}
        </button>
      </div>
    );
  }

  return (
    <div className={containerClassName}>
      <div className={bodyClassName} id={bodyId}>
        {children}
      </div>
      <div className="px-3 pb-3 pt-1">
        <button
          type="button"
          className={buttonClassName}
          aria-controls={bodyId}
          aria-expanded={true}
          onClick={() => setIsExpanded(false)}
        >
          {collapseLabel}
        </button>
      </div>
    </div>
  );
}
