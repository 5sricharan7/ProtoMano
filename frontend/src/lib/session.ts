// Session boundary: manages authentication state and query cache.
// JWT is stored in localStorage and automatically attached to requests.
import { queryClient } from "./queryClient";
import { apiPost } from "./api";
import { clearToken } from "./auth";

// Call after every successful login/signup.
export function beginSession(): void {
  queryClient.clear();
}

// Call from every sign-out control; the hard redirect resets all in-memory state.
export async function endSession(redirectTo: string = "/login"): Promise<void> {
  try {
    await apiPost("/auth/logout");
  } catch {
    // Ignore logout errors - proceed with local cleanup
  } finally {
    clearToken();
    queryClient.clear();
    window.location.assign(redirectTo);
  }
}
