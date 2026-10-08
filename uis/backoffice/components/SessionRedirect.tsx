"use client";

import { SESSION_EXPIRED_EVENT } from "@/lib/token";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

export function SessionRedirect() {
  const router = useRouter();
  const redirecting = useRef(false);

  useEffect(() => {
    const onExpired = () => {
      if (redirecting.current) {
        return;
      }
      if (window.location.pathname === "/login") {
        return;
      }
      redirecting.current = true;
      router.replace("/login");
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => {
      window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
      redirecting.current = false;
    };
  }, [router]);

  return null;
}
