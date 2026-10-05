import { stageLabel } from "@/lib/labels";
import type { CandidateStage } from "@/types/api";

export function StageBadge({ stage }: { stage: CandidateStage }) {
  return (
    <span className="inline-flex rounded-md bg-[var(--surface-muted)] px-2 py-1 text-xs font-semibold text-[var(--ink)]">
      {stageLabel(stage)}
    </span>
  );
}
