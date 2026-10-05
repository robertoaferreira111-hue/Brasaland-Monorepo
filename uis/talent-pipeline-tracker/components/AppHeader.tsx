import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--accent)]">
            Brasaland Digital
          </p>
          <Link href="/" className="text-xl font-semibold tracking-tight text-[var(--ink)]">
            People &amp; Talent
          </Link>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            Executive Assistant pipeline · Medellín HQ
          </p>
        </div>
        <nav className="flex items-center gap-3">
          <Link
            href="/"
            className="text-sm font-medium text-[var(--muted)] transition hover:text-[var(--ink)]"
          >
            Candidates
          </Link>
          <Link
            href="/candidates/new"
            className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)]"
          >
            Register candidate
          </Link>
        </nav>
      </div>
    </header>
  );
}
