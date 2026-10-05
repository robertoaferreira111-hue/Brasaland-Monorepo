import { Suspense } from "react";
import { EditCandidateLoader } from "@/components/EditCandidateLoader";
import { FeedbackBanner } from "@/components/FeedbackBanner";

type EditCandidatePageProps = {
  params: Promise<{ id: string }>;
};

export default async function EditCandidatePage({
  params,
}: EditCandidatePageProps) {
  const { id } = await params;
  return (
    <Suspense
      fallback={<FeedbackBanner tone="info" message="Loading candidate…" />}
    >
      <EditCandidateLoader id={id} />
    </Suspense>
  );
}
