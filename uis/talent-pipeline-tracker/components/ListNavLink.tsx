"use client";

import Link from "next/link";
import { useSyncExternalStore, type ReactNode } from "react";
import {
  getListHref,
  subscribeListHref,
} from "@/lib/listNavigation";

/** Client link back to the candidate list, restoring filters/search/page when available. */
export function ListNavLink({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const href = useSyncExternalStore(
    subscribeListHref,
    getListHref,
    () => "/",
  );

  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
