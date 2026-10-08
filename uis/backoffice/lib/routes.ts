export const PROTECTED_PATHS = ["/account"] as const;

export const PUBLIC_AUTH_PATHS = ["/login", "/register"] as const;

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
}
