"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

/** Native modal semantics provide keyboard containment, Escape and focus return. */
export default function ReviewDialog({ open, onClose, title, children }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const element = dialog.current;
    if (open && element && !element.open) element.showModal();
    if (!open && element?.open) element.close();
  }, [open]);
  return <dialog ref={dialog} className="builder-review-dialog" aria-labelledby={titleId}
    onCancel={onClose} onClose={onClose} onKeyDown={event => {
      if (event.key !== "Tab") return;
      const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea, summary, [tabindex]"))
        .filter(element => element.tabIndex >= 0 && !element.matches(":disabled") && element.getClientRects().length > 0
          && Array.from(event.currentTarget.querySelectorAll("details:not([open])")).every(closed => !closed.contains(element) || closed.firstElementChild === element));
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first && last) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last && first) { event.preventDefault(); first.focus(); }
    }}>
    <header><h2 id={titleId}>{title}</h2><button type="button" onClick={onClose} aria-label={`Close ${title}`}>Close</button></header>
    <div className="builder-review-dialog-body">{children}</div>
  </dialog>;
}
