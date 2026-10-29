import { apiFetch } from "@/lib/session";

export type Tokens = { access_token: string; refresh_token: string };
export type ProfileFields = { name: string; phone: string; address: string };

export const login = (email: string, password: string) =>
  apiFetch("/auth/login", { auth: false, method: "POST", body: JSON.stringify({ email, password }) });

export const register = (email: string, password: string, profile: ProfileFields) =>
  apiFetch("/users", { auth: false, method: "POST", body: JSON.stringify({ email, password, ...profile }) });

export const forgotPassword = (email: string) =>
  apiFetch("/auth/forgot-password", { auth: false, method: "POST", body: JSON.stringify({ email }) });

export const resetPassword = (token: string, newPassword: string) =>
  apiFetch("/auth/reset-password", {
    auth: false,
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });

export const changePassword = (currentPassword: string, newPassword: string) =>
  apiFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
