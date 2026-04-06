"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type PopoverPosition = {
  top: number;
  left: number;
};

const VIEWPORT_PADDING = 16;
const POPOVER_OFFSET = 12;

export function ShowOutlookPopover() {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<PopoverPosition | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    const updatePosition = () => {
      const button = buttonRef.current;
      const popover = popoverRef.current;
      if (!button || !popover) {
        return;
      }

      const buttonRect = button.getBoundingClientRect();
      const popoverWidth = popover.offsetWidth;
      const popoverHeight = popover.offsetHeight;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const roomBelow = viewportHeight - buttonRect.bottom - VIEWPORT_PADDING;
      const roomAbove = buttonRect.top - VIEWPORT_PADDING;
      const placeBelow = roomBelow >= popoverHeight || roomBelow >= roomAbove;

      const unclampedLeft = buttonRect.left + buttonRect.width / 2 - popoverWidth / 2;
      const left = Math.max(
        VIEWPORT_PADDING,
        Math.min(unclampedLeft, viewportWidth - popoverWidth - VIEWPORT_PADDING),
      );
      const unclampedTop = placeBelow
        ? buttonRect.bottom + POPOVER_OFFSET
        : buttonRect.top - popoverHeight - POPOVER_OFFSET;
      const top = Math.max(
        VIEWPORT_PADDING,
        Math.min(unclampedTop, viewportHeight - popoverHeight - VIEWPORT_PADDING),
      );

      setPosition({ top, left });
    };

    const rafId = window.requestAnimationFrame(updatePosition);

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (
        target &&
        !buttonRef.current?.contains(target) &&
        !popoverRef.current?.contains(target)
      ) {
        setOpen(false);
      }
    };

    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("pointerdown", handlePointerDown);

    return () => {
      window.cancelAnimationFrame(rafId);
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [open]);

  const closeOnBlur = () => {
    window.requestAnimationFrame(() => {
      const active = document.activeElement;
      if (
        active &&
        !buttonRef.current?.contains(active) &&
        !popoverRef.current?.contains(active)
      ) {
        setOpen(false);
      }
    });
  };

  return (
    <>
      <button
        ref={buttonRef}
        aria-controls="show-outlook-popover"
        aria-expanded={open}
        aria-label="Explain show outlook"
        className="flex size-4 items-center justify-center rounded-full border border-outline-variant/30 text-[9px] text-on-surface-variant transition hover:border-primary hover:text-primary focus-visible:border-primary focus-visible:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        onBlur={closeOnBlur}
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        type="button"
      >
        i
      </button>

      {typeof document !== "undefined" && open
        ? createPortal(
            <div
              id="show-outlook-popover"
              ref={popoverRef}
              className="fixed z-[140] w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-outline-variant/30 bg-surface px-3 py-3 text-left text-xs leading-5 text-on-surface-variant shadow-xl md:w-72"
              style={{
                left: position?.left ?? VIEWPORT_PADDING,
                top: position?.top ?? VIEWPORT_PADDING,
              }}
            >
              <p>A plain-language read of the current top 10 prediction board.</p>
              <p className="mt-2">
                <span className="font-semibold text-on-surface">Heavy rotation:</span>{" "}
                top songs were played recently and the board leans familiar.
              </p>
              <p>
                <span className="font-semibold text-on-surface">Deep cuts expected:</span>{" "}
                top songs have been missing longer and the board leans less frequent.
              </p>
              <p>
                <span className="font-semibold text-on-surface">Bust-out potential:</span>{" "}
                the wider ranked list includes more long-gap songs than usual.
              </p>
              <p>
                <span className="font-semibold text-on-surface">Balanced expectations:</span>{" "}
                a mix of active rotation songs and longer-gap reach candidates.
              </p>
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
