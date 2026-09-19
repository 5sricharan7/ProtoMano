// JWT authentication utilities for Manobal-AI frontend.
// Stores JWT in localStorage and provides token management.

import type { AuthToken } from "./types";

const TOKEN_KEY = "manobal_auth_token";
const USER_KEY = "manobal_auth_user";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function setAuthData(authData: AuthToken): void {
  setToken(authData.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify({
    user_id: authData.user_id,
    username: authData.username,
    role: authData.role,
  }));
}

export function getAuthData(): { user_id: string; username: string; role: string } | null {
  const data = localStorage.getItem(USER_KEY);
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}
