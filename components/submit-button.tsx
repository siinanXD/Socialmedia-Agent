"use client";

import { useFormStatus } from "react-dom";

/** Sperrt sich, solange das umgebende Formular sendet: kein Doppelklick, sichtbare Ladeanzeige. */
export function SubmitButton({ label, pendingLabel }: { label: string; pendingLabel: string }) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} aria-busy={pending}>
      {pending && <span className="spinner" aria-hidden="true" />}
      {pending ? pendingLabel : label}
    </button>
  );
}
