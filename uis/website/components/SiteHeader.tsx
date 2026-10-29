"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

type SiteHeaderProps = {
  brasaHref?: string;
};

export function SiteHeader({ brasaHref = "/application" }: SiteHeaderProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const home = pathname === "/";
  const onApplication = pathname === "/application";

  const locationsHref = home ? "#locations" : "/#locations";
  const menuHref = home ? "#menu" : "/#menu";
  const contactHref = home ? "#contact" : "/#contact";

  return (
    <header className="border-b border-stone-300 bg-stone-100">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link
          className="font-serif text-2xl font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          href="/"
        >
          Brasaland
        </Link>
        <button
          className="min-h-11 rounded-full border border-stone-400 px-3 py-2 text-sm md:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          type="button"
          aria-expanded={open}
          aria-controls="site-nav"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Close navigation" : "Open navigation"}
        </button>
      </div>
      <nav
        id="site-nav"
        className={`mx-auto max-w-6xl flex-col gap-1 px-4 pb-4 md:flex md:flex-row md:px-4 md:pb-3 ${
          open ? "flex" : "hidden md:flex"
        }`}
        aria-label="Primary"
      >
        <Link
          className="rounded-full px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          href="/"
          aria-current={home ? "page" : undefined}
        >
          Home
        </Link>
        <a
          className="rounded-full px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          href={locationsHref}
        >
          Locations
        </a>
        <a
          className="rounded-full px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          href={menuHref}
        >
          Menu
        </a>
        <Link
          className="rounded-full px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          href={brasaHref}
          aria-current={onApplication ? "page" : undefined}
        >
          Brasa Points
        </Link>
        <a
          className="rounded-full px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          href={contactHref}
        >
          Contact
        </a>
      </nav>
    </header>
  );
}
