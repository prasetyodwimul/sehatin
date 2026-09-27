import { apiFetch } from "@/lib/api";

export type AuthUser = {
  id: string;
  email: string;
  created_at: string;
  full_name?: string | null;
  display_name?: string | null;
  avatar_data_url?: string | null;
  bio?: string | null;
};

export type AuthResponse = {
  user: AuthUser;
  message: string;
};

export type ProfileUpdatePayload = {
  full_name?: string | null;
  display_name?: string | null;
  avatar_data_url?: string | null;
  bio?: string | null;
};

export function getCurrentUser() {
  return apiFetch<AuthUser>("/api/auth/me");
}

export function registerAccount(email: string, password: string) {
  return apiFetch<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function loginAccount(email: string, password: string) {
  return apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function updateAccountProfile(payload: ProfileUpdatePayload) {
  return apiFetch<AuthUser>("/api/auth/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function logoutAccount() {
  return apiFetch<void>("/api/auth/logout", { method: "POST" });
}
