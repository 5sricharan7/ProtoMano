import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, Fingerprint, HeartHandshake, ShieldCheck } from "lucide-react";
import { apiPost } from "@/lib/api";
import { HERO_BACKGROUND_URL } from "@/lib/config";
import { setAuthData } from "@/lib/auth";
import { beginSession } from "@/lib/session";
import type { AuthToken, DemoSeedResponse } from "@/lib/types";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: async () => {
      // Step 1: Authenticate with backend
      const authResponse = await apiPost<AuthToken>("/auth/login", { username, password });
      
      // Step 2: Store JWT and user data
      setAuthData(authResponse);
      beginSession();
      
      // Step 3: Seed demo data (now authenticated)
      const seedResponse = await apiPost<DemoSeedResponse>("/demo/seed", {});
      
      return { authResponse, seedResponse };
    },
    onSuccess: (data) => {
      // Navigate based on role
      if (data.authResponse.role === "WELFARE_OFFICER") {
        navigate("/officer");
      } else if (data.authResponse.role === "PERSONNEL") {
        navigate("/personnel");
      } else {
        navigate("/officer");
      }
    },
    onError: (err: any) => {
      if (err?.status === 401) {
        setError("Invalid username or password");
      } else if (err?.status === 403) {
        setError("Access denied. Welfare Officer role required.");
      } else if (err?.status === 404 || err?.status === 0) {
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
      setError("Username and password are required");
      return;
    }
    
    loginMutation.mutate();
  }

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
            backgroundImage: `linear-gradient(90deg, rgba(0, 26, 23, .89), rgba(0, 26, 23, .30)), url(${HERO_BACKGROUND_URL})` 
          }}
        >
          <div>
            <span className="demo-story-kicker">DEMO ENVIRONMENT</span>
            <h1>Every signal<br /><em>deserves care.</em></h1>
            <i className="demo-story-rule" />
            <p>
              Step into a synthetic welfare workspace built around the real uploaded model. 
              Authenticate with your Welfare Officer credentials to access the full SIH story.
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
            <span className="demo-command-kicker">Welfare Officer Access</span>
            <h2>Sign in to your<br /><em>demo workspace.</em></h2>
            <p>
              Enter your Welfare Officer credentials to authenticate and seed the synthetic demonstration environment.
            </p>
            
            <form onSubmit={handleSubmit} data-testid="login-form">
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
                data-testid="enter-demo-button"
              >
                <HeartHandshake size={20} />
                {loginMutation.isPending ? "Authenticating…" : "Sign in as Welfare Officer"}
                <ArrowRight size={20} />
              </button>

              {error && (
                <p className="login-error" data-testid="login-error">
                  {error}
                </p>
              )}
            </form>

            <div className="demo-notice">
              <ShieldCheck size={19} />
              <span>
                Synthetic DEMO DATA is generated for presentation only. Risk results still come from 
                the real `/api/predict` endpoint and uploaded LightGBM artifact.
              </span>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}