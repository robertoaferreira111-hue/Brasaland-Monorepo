const DEFAULT_API_BASE = "http://127.0.0.1:8000";

export function resolveApiBase(): string {
  if (typeof window === "undefined") {
    return (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE).replace(/\/+$/, "");
  }

  const override = new URLSearchParams(window.location.search).get("api");
  if (override) return override.replace(/\/+$/, "");

  const { hostname, protocol } = window.location;
  if (hostname.endsWith(".app.github.dev")) {
    return `${protocol}//${hostname.replace(/-\d+(?=\.app\.github\.dev$)/, "-8000")}`;
  }

  return (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE).replace(/\/+$/, "");
}
