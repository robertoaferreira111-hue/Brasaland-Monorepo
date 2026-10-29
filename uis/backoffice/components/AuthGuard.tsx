"use client";

import { hasAccessToken, redirectToLogin } from "@/lib/session";
import { useEffect, useState, type ReactNode } from "react";

export default function AuthGuard({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!hasAccessToken()) redirectToLogin();
    else setReady(true);
  }, []);
  return ready ? children : <main><p className="status-line">Checking session…</p></main>;
}
