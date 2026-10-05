import { EditCandidateLoader } from "@/components/EditCandidateLoader";

type EditCandidatePageProps = {
  params: Promise<{ id: string }>;
};

export default async function EditCandidatePage({
  params,
}: EditCandidatePageProps) {
  const { id } = await params;
  return <EditCandidateLoader id={id} />;
}
