"use client";

import { useEffect, useLayoutEffect, useRef } from "react";

// One stack for nested PMS dialogs. No data, requests or booking decisions here.
const dialogs: HTMLElement[] = [];
let originalOverflow = "";
const candidates = 'button,input,select,textarea,a[href],[tabindex]';
function focusable(root: HTMLElement) {
  return Array.from(root.querySelectorAll<HTMLElement>(candidates)).filter(element =>
    element.tabIndex >= 0 && !element.matches(":disabled") &&
    !element.closest('[hidden],[inert],[aria-hidden="true"]') &&
    element.getClientRects().length > 0 && getComputedStyle(element).visibility !== "hidden");
}

/** Opt-in FL2 presentation only: focus stays in the top dialog and returns on close. */
export function usePmsDialog(onClose: () => void, busy: boolean) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const latest = useRef({ onClose, busy });
  useLayoutEffect(() => { latest.current = { onClose, busy }; }, [onClose, busy]);
  useEffect(() => {
    const root = dialogRef.current;
    if (!root || document.documentElement.dataset.marinaUi !== "future-luxury") return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (dialogs.length === 0) { originalOverflow = document.body.style.overflow; document.body.style.overflow = "hidden"; }
    dialogs.push(root);
    const top = () => dialogs.at(-1) === root;
    const focusFirst = () => (focusable(root)[0] || root).focus({ preventScroll: true });
    focusFirst();
    const keydown = (event: KeyboardEvent) => {
      if (!top() || event.defaultPrevented) return;
      if (event.key === "Escape") {
        event.preventDefault(); event.stopPropagation();
        if (!latest.current.busy) latest.current.onClose();
      } else if (event.key === "Tab") {
        const items = focusable(root);
        const first = items[0], last = items.at(-1);
        if (!first) { event.preventDefault(); root.focus({ preventScroll: true }); }
        else if (event.shiftKey && (document.activeElement === first || document.activeElement === root)) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || document.activeElement === root || !root.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
      }
    };
    const focusin = (event: FocusEvent) => { if (top() && event.target instanceof Node && !root.contains(event.target)) focusFirst(); };
    document.addEventListener("keydown", keydown);
    document.addEventListener("focusin", focusin);
    return () => {
      document.removeEventListener("keydown", keydown);
      document.removeEventListener("focusin", focusin);
      const index = dialogs.lastIndexOf(root);
      if (index !== -1) dialogs.splice(index, 1);
      if (dialogs.length === 0) document.body.style.overflow = originalOverflow;
      queueMicrotask(() => {
        const parent = dialogs.at(-1);
        if (parent) { if (previous?.isConnected && parent.contains(previous)) previous.focus({ preventScroll: true }); }
        else if (previous?.isConnected) previous.focus({ preventScroll: true });
        else document.querySelector<HTMLElement>(".owner-grid-scroll")?.focus({ preventScroll: true });
      });
    };
  }, []);
  return dialogRef;
}
