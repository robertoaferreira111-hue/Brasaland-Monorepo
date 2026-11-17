import KnowledgeQuery from "@/components/KnowledgeQuery";
import { PublicHeader } from "@/components/SiteHeader";

export default function KnowledgePage() {
  return (
    <>
      <PublicHeader />
      <main id="main" tabIndex={-1}>
        <header className="page-intro">
          <h1>Ask the manuals</h1>
          <p>
            Location managers can ask how Brasa Points, waste rules, allergens, and supplier orders work.
            Answers come only from the official manuals.
          </p>
        </header>
        <KnowledgeQuery />
      </main>
      <footer className="site-footer">
        <p>© 2025 Brasaland. All rights reserved.</p>
      </footer>
    </>
  );
}
