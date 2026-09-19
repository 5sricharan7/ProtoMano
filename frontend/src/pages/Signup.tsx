import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Fingerprint,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { apiPost, ApiError } from "@/lib/api";
import { HERO_BACKGROUND_URL } from "@/lib/config";
import type { AuthToken } from "@/lib/types";

export default function Signup() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  function validate(): string | null {
    const name = username.trim();
    if (!name) return "Enter a username.";
    if (name.length < 2) return "Username must be at least 2 characters.";
    if (name.length > 120) return "Username must be 120 characters or fewer.";
    if (!password) return "Enter a password.";
    if (password.length < 8) return "Password must be at least 8 characters.";
    if (password.length > 255) return "Password must be 255 characters or fewer.";
    if (password !== confirm) return "Passwords do not match.";
    return null;
  }

  function messageFor(err: unknown): string {
    if (err instanceof ApiError) {
      const detail = (err.body as { detail?: unknown } | null)?.detail;
      const text = typeof detail === "string" ? detail : "";
      if (err.status === 409) return "That username is already in use. Try another.";
      if (err.status === 403) return text || "Registration is limited to Personnel accounts.";
      if (err.status === 422) {
        return "Please check the requirements: username 2–120 characters, password at least 8 characters.";
      }
      if (err.status === 404 || err.status === 500) {
        return err.status === 404
          ? "Backend server unavailable. Please ensure the API is running."
          : "Something went wrong on the server. Please try again.";
      }
      return text || `Registration failed (${err.status}). Please try again.`;
    }
    return "Backend server unavailable. Please ensure the API is running.";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setPending(true);
    try {
      await apiPost<AuthToken>("/auth/register", {
        username: username.trim(),
        password,
        role: "PERSONNEL",
      });
      setDone(true);
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="reference-login">
      <header className="demo-header">
        <Link to="/" className="reference-brand" data-testid="signup-brand-link">
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
            <span className="demo-story-kicker">PERSONNEL SIGNUP</span>
            <h1>Your welfare,<br /><em>your private view.</em></h1>
            <i className="demo-story-rule" />
            <p>
              Create a self-service Personnel account to review your own signals and stay
              human-in-the-loop. Access is PERSONNEL only and verified by the backend.
            </p>
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
            <Link to="/login" className="gate-back" data-testid="signup-back-link">
              <ArrowLeft size={14} /> Back to workspace selection
            </Link>
            <span className="demo-command-kicker">PERSONNEL WORKSPACE</span>
            <h2>Create a personnel<br /><em>account.</em></h2>
            <p>
              Registration creates a PERSONNEL account only. Officers and Commanders are
              provisioned by the backend and can never be requested from this form.
            </p>
            <div className="workspace-role-chip">
              <UserRound size={13} /> Personnel only
            </div>

            {done ? (
              <>
                <div className="signup-success" data-testid="signup-success">
                  <span className="signup-success-icon"><CheckCircle2 size={26} /></span>
                  <div>
                    <h3>Account created</h3>
                    <p>
                      Your Personnel account is ready. Sign in to view your private welfare
                      workspace. You have not been signed in automatically.
                    </p>
                  </div>
                </div>
                <Link to="/login/personnel" className="demo-continue signup-login-link" data-testid="signup-go-login-link">
                  Go to Personnel Login <ArrowRight size={19} />
                </Link>
              </>
            ) : (
              <form onSubmit={handleSubmit} className="gate-form" data-testid="signup-form" noValidate>
                <div className="demo-login-fields">
                  <div className="demo-field">
                    <label htmlFor="signup-username">Username</label>
                    <input
                      id="signup-username"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="Choose a username"
                      disabled={pending}
                      autoComplete="username"
                      maxLength={120}
                      data-testid="signup-username-input"
                    />
                  </div>
                  <div className="demo-field">
                    <label htmlFor="signup-password">Password</label>
                    <input
                      id="signup-password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="At least 8 characters"
                      disabled={pending}
                      autoComplete="new-password"
                      maxLength={255}
                      data-testid="signup-password-input"
                    />
                  </div>
                  <div className="demo-field">
                    <label htmlFor="signup-confirm">Confirm password</label>
                    <input
                      id="signup-confirm"
                      type="password"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      placeholder="Re-enter your password"
                      disabled={pending}
                      autoComplete="new-password"
                      maxLength={255}
                      data-testid="signup-confirm-input"
                    />
                  </div>
                </div>

                {error && (
                  <p className="login-error" role="alert" data-testid="signup-error">
                    {error}
                  </p>
                )}

                <button type="submit" className="demo-continue" disabled={pending} data-testid="signup-submit">
                  <ShieldCheck size={19} />
                  {pending ? "Creating account…" : "Create Personnel account"}
                  <ArrowRight size={19} />
                </button>
              </form>
            )}

            <div className="demo-notice">
              <ShieldCheck size={19} />
              <span>
                Synthetic DEMO DATA is generated for presentation only; access is always
                role-checked by the backend before any personnel workspace is shown.
              </span>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}