import { useState } from "react";
import type { ComponentType, FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Command, Fingerprint, HeartHandshake, ShieldCheck, UserRound } from "lucide-react";
import { apiPost } from "@/lib/api";
import { HERO_BACKGROUND_URL } from "@/lib/config";
import { clearToken, setAuthData } from "@/lib/auth";
import { beginSession } from "@/lib/session";
import { queryClient } from "@/lib/queryClient";
import type { AuthToken, DemoSeedResponse, UserRole } from "@/lib/types";

interface WorkspaceMeta {
  role: UserRole;
  label: string;
  kicker: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  accent: "mint" | "commander";
  headline: string;
  headlineEm: string;
  story: string;
}

const WORKSPACES: Record<string, WorkspaceMeta> = {
  officer: {
    role: "WELFARE_OFFICER",
    label: "Welfare Officer",
    kicker: "WELFARE OFFICER WORKSPACE",
    icon: HeartHandshake,
    accent: "mint",
    headline: "Every signal",
    headlineEm: "deserves care.",
    story: "Authenticate as a Welfare Officer to enter the welfare command workspace and coordinate support for personnel.",
  },
  commander: {
    role: "COMMANDER",
    label: "Commander",
    kicker: "COMMANDER WORKSPACE",
    icon: Command,
    accent: "commander",
    headline: "Readiness, with",
    headlineEm: "respect for privacy.",
    story: "Authenticate with your Commander credentials to enter the unit-level welfare intelligence workspace.",
  },
  personnel: {
    role: "PERSONNEL",
    label: "Personnel Teammate",
    kicker: "PERSONNEL WORKSPACE",
    icon: UserRound,
    accent: "mint",
    headline: "Your welfare,",
    headlineEm: "your private view.",
    story: "Authenticate as Personnel to enter your private welfare workspace and review your own signals.",
  },
};

const HOME_PATHS: Record<UserRole, string> = {
  PERSONNEL: "/personnel",
  WELFARE_OFFICER: "/officer",
  COMMANDER: "/command",
  ADMIN: "/admin",
};

const ROLE_MISMATCH = "Your account does not have access to this workspace.";

export default function RoleLogin() {
  const params = useParams<{ workspace: string }>();
  const navigate = useNavigate();
  const meta = WORKSPACES[params.workspace ?? ""];
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: async () => {
      const authResponse = await apiPost<AuthToken>("/auth/login", { username, password });
      setAuthData(authResponse);
      beginSession();
      // Seeding is welfare-officer specific: Commanders and Personnel never seed.
      if (authResponse.role === "WELFARE_OFFICER") {
        await apiPost<DemoSeedResponse>("/demo/seed", {});
      }
      return authResponse;
    },
    onSuccess: (authResponse) => {
      if (authResponse.role !== meta.role) {
        clearToken();
        queryClient.clear();
        setError(ROLE_MISMATCH);
        return;
      }
      navigate(HOME_PATHS[authResponse.role], { replace: true });
    },
    onError: (err: unknown) => {
      const status = (err as { status?: number }).status;
      if (status === 401) {
        setError("Invalid username or password.");
      } else if (status === 403) {
        setError("This account cannot access the workspace.");
      } else if (status === 404 || status === 0) {
        setError("Backend server unavailable. Please ensure the API is running.");
      } else {
        setError("Login failed. Please try again.");
      }
    },
  });

  if (!meta) {
    return <Navigate to="/login" replace />;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!username.trim() || !password) {
      setError("Username and password are required.");
      return;
    }
    loginMutation.mutate();
  }

  const Icon = meta.icon;
  const isCommander = meta.accent === "commander";

  return (
    <div className="reference-login">
      <header className="demo-header">
        <Link to="/" className="reference-brand" data-testid="login-brand-link">
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
          className="demo-story"
          style={{
            backgroundImage: `linear-gradient(105deg, rgba(246,243,234,.96) 0%, rgba(255,253,248,.90) 40%, rgba(255,253,248,.62) 72%, rgba(255,253,248,.45) 100%), url(${HERO_BACKGROUND_URL})`,
          }}
        >
          <div>
            <span className="demo-story-kicker">DEMO ENVIRONMENT</span>
            <h1>{meta.headline}<br /><em>{meta.headlineEm}</em></h1>
            <i className="demo-story-rule" />
            <p>{meta.story}</p>
          </div>
          <footer>
            <span>
              <ShieldCheck size={20} /> HUMAN-IN-THE-LOOP • WELFARE-ONLY PURPOSE
            </span>
            <strong>People. Prepared. Protected.</strong>
          </footer>
        </section>
        <main className="demo-command">
          <div className="demo-command-inner">
            <Link to="/login" className="gate-back" data-testid="workspace-back-link">
              <ArrowLeft size={14} /> Back to workspace selection
            </Link>
            <span className="demo-command-kicker">{meta.kicker}</span>
            <h2>Secure workspace<br /><em>access.</em></h2>
            <p>
              Enter your credentials to enter this workspace. Access is verified against
              your account role by the backend.
            </p>
            <div className={`workspace-role-chip ${isCommander ? "workspace-role-chip--commander" : ""}`}>
              <Icon size={13} /> {meta.label}
            </div>

            <form onSubmit={handleSubmit} data-testid="login-form" className="gate-form">
              <div className="demo-login-fields">
                <div className="demo-field">
                  <label htmlFor="username">Username</label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter username"
                    disabled={loginMutation.isPending}
                    data-testid="login-username-input"
                    autoComplete="username"
                  />
                </div>
                <div className="demo-field">
                  <label htmlFor="password">Password</label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    disabled={loginMutation.isPending}
                    data-testid="login-password-input"
                    autoComplete="current-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="demo-continue"
                disabled={loginMutation.isPending}
                data-testid="login-submit-button"
              >
                <ShieldCheck size={19} />
                {loginMutation.isPending ? "Authenticating…" : "Sign in securely"}
                <ArrowRight size={19} />
              </button>

              {error && (
                <p className={`login-error ${error === ROLE_MISMATCH ? "login-error--mismatch" : ""}`} role="alert" data-testid="login-error">
                  {error}
                </p>
              )}
            </form>

            <div className="demo-notice">
              <ShieldCheck size={19} />
              <span>
                Synthetic DEMO DATA is generated for presentation only; predictions still
                come from the real model and every result is role-checked by the backend.
              </span>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}