import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Fingerprint, ShieldCheck } from "lucide-react";
import { apiPost } from "@/lib/api";
import { HERO_BACKGROUND_URL } from "@/lib/config";
import { clearToken, setAuthData } from "@/lib/auth";
import { beginSession } from "@/lib/session";
import { queryClient } from "@/lib/queryClient";
import type { AuthToken } from "@/lib/types";

const NOT_ADMIN = "This account does not have administrator access.";

export default function AdminLogin() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: async () => {
      const authResponse = await apiPost<AuthToken>("/auth/login", { username, password });
      setAuthData(authResponse);
      beginSession();
      return authResponse;
    },
    onSuccess: (authResponse) => {
      if (authResponse.role !== "ADMIN") {
        clearToken();
        queryClient.clear();
        setError(NOT_ADMIN);
        return;
      }
      navigate("/admin", { replace: true });
    },
    onError: (err: unknown) => {
      const status = (err as { status?: number }).status;
      if (status === 401) {
        setError("Invalid username or password.");
      } else if (status === 403) {
        setError("This account cannot access the admin workspace.");
      } else if (status === 404 || status === 0) {
        setError("Backend server unavailable. Please ensure the API is running.");
      } else {
        setError("Login failed. Please try again.");
      }
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!username.trim() || !password) {
      setError("Username and password are required.");
      return;
    }
    loginMutation.mutate();
  }

  return (
    <div className="reference-login">
      <header className="demo-header">
        <Link to="/" className="reference-brand" data-testid="admin-brand-link">
          <span className="reference-brand-mark">
            <Fingerprint size={24} />
          </span>
          <span>
            <strong>Manobal<span>-AI</span></strong>
            <small>Welfare Signal</small>
          </span>
        </Link>
        <nav>
          <Link to="/">Home</Link>
          <Link to="/#how-it-works">How it works</Link>
          <Link to="/#ethics">Privacy & ethics</Link>
        </nav>
      </header>
      <div className="demo-layout">
        <section
          className="demo-story admin-story"
          style={{
            backgroundImage: `linear-gradient(105deg, rgba(246,243,234,.96) 0%, rgba(255,253,248,.90) 40%, rgba(255,253,248,.62) 72%, rgba(255,253,248,.45) 100%), url(${HERO_BACKGROUND_URL})`,
          }}
        >
          <div>
            <span className="demo-story-kicker">DEMO ENVIRONMENT</span>
            <h1>Restricted<br /><em>access.</em></h1>
            <i className="demo-story-rule" />
            <p>
              The administration workspace governs system accounts and access controls.
              Only verified Administrators can enter.
            </p>
          </div>
          <footer>
            <span>
              <ShieldCheck size={20} /> CUSTODIAN ROLE • ACCOUNT GOVERNANCE
            </span>
            <strong>People. Prepared. Protected.</strong>
          </footer>
        </section>
        <main className="demo-command">
          <div className="demo-command-inner">
            <Link to="/login" className="gate-back" data-testid="admin-back-link">
              <ArrowLeft size={14} /> Back to workspace selection
            </Link>
            <span className="demo-command-kicker">ADMINISTRATOR ACCESS</span>
            <h2>Administrators<br /><em>only.</em></h2>
            <p>
              Enter your credentials. Your role is verified by the backend — the
              sign-in view never decides your clearance.
            </p>
            <div className="workspace-role-chip workspace-role-chip--admin">
              <ShieldCheck size={13} /> Administrator
            </div>

            <form onSubmit={handleSubmit} data-testid="admin-login-form" className="gate-form">
              <div className="demo-login-fields">
                <div className="demo-field">
                  <label htmlFor="admin-username">Username</label>
                  <input
                    id="admin-username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter username"
                    disabled={loginMutation.isPending}
                    data-testid="admin-username-input"
                    autoComplete="username"
                  />
                </div>
                <div className="demo-field">
                  <label htmlFor="admin-password">Password</label>
                  <input
                    id="admin-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    disabled={loginMutation.isPending}
                    data-testid="admin-password-input"
                    autoComplete="current-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="demo-continue"
                disabled={loginMutation.isPending}
                data-testid="admin-submit-button"
              >
                <ShieldCheck size={19} />
                {loginMutation.isPending ? "Authenticating…" : "Authenticate"}
                <ArrowRight size={19} />
              </button>

              {error && (
                <p
                  className={`login-error ${error === NOT_ADMIN ? "login-error--mismatch" : ""}`}
                  role="alert"
                  data-testid="admin-login-error"
                >
                  {error}
                </p>
              )}
            </form>

            <div className="demo-notice">
              <ShieldCheck size={19} />
              <span>
                Administrator access is granted only to accounts the backend
                confirms as ADMIN. No administrator self-registration exists.
              </span>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}