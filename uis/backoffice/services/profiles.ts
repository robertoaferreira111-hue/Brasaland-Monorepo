import { apiFetch } from "@/lib/session";
import type { ProfileFields } from "./auth";

export const getProfile = () => apiFetch("/auth/me");

export const updateProfile = (profile: ProfileFields) =>
  apiFetch("/profiles/me", { method: "PUT", body: JSON.stringify(profile) });
