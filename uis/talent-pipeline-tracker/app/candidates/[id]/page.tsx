import { Suspense } from "react";
import { CandidateDetail } from "@/components/CandidateDetail";
import { FeedbackBanner } from "@/components/FeedbackBanner";

type CandidatePageProps = {
  params: Promise<{ id: string }>;
};

export default async function CandidatePage({ params }: CandidatePageProps) {
  const { id } = await params;
  return (
    <Suspense
      fallback={<FeedbackBanner tone="info" message="Loading candidate…" />}
    >
      <CandidateDetail id={id} />
    </Suspense>
  );
}
