import { Suspense } from "react";
import { CandidateForm } from "@/components/CandidateForm";
import { ListNavLink } from "@/components/ListNavLink";

export default function NewCandidatePage() {
  return (
    <div className="grid gap-4">
      <div>
        <p className="text-sm text-[var(--muted)]">
          <Suspense fallback={<span>Candidates</span>}>
            <ListNavLink className="hover:underline">Candidates</ListNavLink>
          </Suspense>{" "}
          / Register
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)]">
          Register candidate
        </h1>
        <p className="text-sm text-[var(--muted)]">
          Add applicants who reach Brasaland through channels outside the main
          Executive Assistant intake.
        </p>
      </div>
      <CandidateForm mode="create" />
    </div>
  );
}
