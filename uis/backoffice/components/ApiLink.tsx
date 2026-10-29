"use client";

import { appHref } from "@/lib/session";
import Link from "next/link";
import { useEffect, useState, type ComponentProps } from "react";

export default function ApiLink({ href, ...props }: Omit<ComponentProps<typeof Link>, "href"> & { href: string }) {
  const [resolvedHref, setResolvedHref] = useState(href);
  useEffect(() => setResolvedHref(appHref(href)), [href]);
  return <Link href={resolvedHref} {...props} />;
}
