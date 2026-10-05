import { statusLabel } from "@/lib/labels";
import type { CandidateStatus } from "@/types/candidate";

const statusStyles: Record<CandidateStatus, string> = {
  received: "bg-sky-100 text-sky-900",
  in_progress: "bg-amber-100 text-amber-950",
  selected: "bg-emerald-100 text-emerald-900",
  discarded: "bg-stone-200 text-stone-800",
};

export function StatusBadge({ status }: { status: CandidateStatus }) {
  return (
    <span
      className={`inline-flex rounded-md px-2 py-1 text-xs font-semibold ${statusStyles[status]}`}
    >
      {statusLabel(status)}
    </span>
  );
}
