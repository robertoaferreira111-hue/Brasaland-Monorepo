"use client";

import { hasAccessToken } from "@/lib/token";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(hasAccessToken() ? "/account" : "/login");
  }, [router]);

  return (
    <main id="main" tabIndex={-1} className="mx-auto w-full max-w-md px-4 py-16">
      <p role="status">Opening Brasaland…</p>
    </main>
  );
}
