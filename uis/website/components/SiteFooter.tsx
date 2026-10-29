export function SiteFooter() {
  return (
    <footer className="border-t border-stone-300 bg-stone-950 text-stone-50">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm sm:flex-row sm:items-center sm:justify-between">
        <p>© 2025 Brasaland. All rights reserved.</p>
        <p>
          <a
            className="underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-50"
            href="https://instagram.com/brasaland"
            rel="noopener noreferrer"
            target="_blank"
          >
            Instagram
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          <span aria-hidden="true"> | </span>
          <a
            className="underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-50"
            href="https://facebook.com/brasaland"
            rel="noopener noreferrer"
            target="_blank"
          >
            Facebook
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </p>
      </div>
    </footer>
  );
}
