import { Suspense } from "react";
import { CandidateFilters } from "@/components/CandidateFilters";
import { CandidateList } from "@/components/CandidateList";
import { FeedbackBanner } from "@/components/FeedbackBanner";

export default function HomePage() {
  return (
    <div className="grid gap-4">
      <Suspense
        fallback={<FeedbackBanner tone="info" message="Loading filters…" />}
      >
        <CandidateFilters />
      </Suspense>
      <Suspense
        fallback={<FeedbackBanner tone="info" message="Loading candidates…" />}
      >
        <CandidateList />
      </Suspense>
    </div>
  );
}
