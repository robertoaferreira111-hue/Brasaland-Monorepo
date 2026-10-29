"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";
import { listHrefFromReturnParam } from "@/lib/listNavigation";

/**
 * Link back to the candidate list.
 * On detail pages, restores filters via the authoritative `return` query param.
 * On the list page, keeps the current list query.
 */
export function ListNavLink({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const returnQuery = searchParams.get("return");

  let href = "/";
  if (returnQuery !== null) {
    href = listHrefFromReturnParam(returnQuery);
  } else if (pathname === "/" && searchParams.toString()) {
    href = `/?${searchParams.toString()}`;
  }

  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
