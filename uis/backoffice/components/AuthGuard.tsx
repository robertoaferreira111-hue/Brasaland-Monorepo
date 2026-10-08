"use client";

import { hasAccessToken } from "@/lib/token";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!hasAccessToken()) {
      router.replace("/login");
      return;
    }
    // The token is in localStorage, which exists only after mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one client read gates the protected view
    setReady(true);
  }, [router]);

  if (!ready) {
    return (
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-md px-4 py-16">
        <p role="status">Checking session…</p>
      </main>
    );
  }

  return children;
}
