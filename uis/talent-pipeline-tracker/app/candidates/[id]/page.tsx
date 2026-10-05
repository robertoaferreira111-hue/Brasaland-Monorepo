import { CandidateDetail } from "@/components/CandidateDetail";

type CandidatePageProps = {
  params: Promise<{ id: string }>;
};

export default async function CandidatePage({ params }: CandidatePageProps) {
  const { id } = await params;
  return <CandidateDetail id={id} />;
}
