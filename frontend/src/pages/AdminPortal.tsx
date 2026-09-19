import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Database,
  Fingerprint,
  KeyRound,
  LogOut,
  Plus,
  ServerCog,
  ShieldCheck,
  Users,
} from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { endSession } from "@/lib/session";
import type {
  AdminProvisionRequest,
  AdminSystemStatus,
  ProvisionRole,
} from "@/lib/types";

const PROVISIONABLE_ROLES: { role: ProvisionRole; label: string }[] = [
  { role: "WELFARE_OFFICER", label: "Welfare Officer" },
  { role: "COMMANDER", label: "Commander" },
];

export default function AdminPortal() {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<ProvisionRole>("WELFARE_OFFICER");
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  const statusQuery = useQuery({
    queryKey: ["admin-status"],
    queryFn: () => apiGet<AdminSystemStatus>("/admin/status"),
  });

  const provisionMutation = useMutation({
    mutationFn: async (payload: AdminProvisionRequest) => {
      await apiPost("/admin/users", payload);
    },
    onSuccess: () => {
      setUsername("");
      setPassword("");
      setNotice({
        kind: "success",
        text: "Account created.",
      });
      queryClient.invalidateQueries({ queryKey: ["admin-status"] });
    },
    onError: (err: unknown) => {
      const status = (err as { status?: number }).status;
      if (status === 409) {
        setNotice({ kind: "error", text: "That username is already in use." });
      } else if (status === 422) {
        setNotice({
          kind: "error",
          text: "Invalid input. Use a unique username (2+ characters) and a password of at least 8 characters.",
        });
      } else if (status === 401 || status === 403) {
        setNotice({
          kind: "error",
          text: "Your administrative session was rejected. Please sign in again.",
        });
      } else if (status === 404 || status === 0) {
        setNotice({ kind: "error", text: "Backend server unavailable. Please verify the API is running." });
      } else {
        setNotice({ kind: "error", text: "Provisioning failed. Please try again." });
      }
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    const trimmed = username.trim();
    if (!trimmed || !password) {
      setNotice({ kind: "error", text: "Username and password are required." });
      return;
    }
    provisionMutation.mutate({ username: trimmed, password, role });
  }

  const status = statusQuery.data;
  const statusFailed = statusQuery.isError;

  return (
    <div className="admin-portal" data-testid="admin-portal">
      <header className="admin-header">
        <Link to="/" className="reference-brand" data-testid="admin-portal-brand">
          <span className="reference-brand-mark">
            <Fingerprint size={24} />
          </span>
          <span>
            <strong>Manobal<span>-AI</span></strong>
            <small>Welfare Signal</small>
          </span>
        </Link>
        <nav className="admin-header-nav">
          <Link to="/">Home</Link>
          <button
            type="button"
            className="admin-header-signout"
            onClick={() => {
              void endSession();
            }}
            data-testid="admin-signout-button"
          >
            <LogOut size={14} /> Sign out
          </button>
        </nav>
      </header>

      <main className="admin-main">
        <section className="admin-head">
          <Link to="/login" className="gate-back" data-testid="admin-portal-back">
            <ArrowLeft size={14} /> Back to workspace selection
          </Link>
          <span className="admin-kicker">SYSTEM ADMINISTRATION</span>
          <h1>Controlled<br /><em>access.</em></h1>
          <p>
            Account governance for the welfare platform. Provision officer and
            commander identities only — administrator accounts are never
            created through this interface.
          </p>
        </section>

        <div className="admin-grid">
          <section className="admin-panel admin-panel--provision" data-testid="admin-provision-panel">
            <div className="admin-panel-head">
              <span className="admin-panel-icon">
                <KeyRound size={18} />
              </span>
              <div>
                <h2>Provision account</h2>
                <p>Create a new authorized WELFARE_OFFICER or COMMANDER login.</p>
              </div>
            </div>

            <form className="admin-form" onSubmit={handleSubmit} data-testid="admin-provision-form">
              <div className="admin-field">
                <label htmlFor="admin-new-username">Username</label>
                <input
                  id="admin-new-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. lt_verma"
                  disabled={provisionMutation.isPending}
                  data-testid="provision-username-input"
                  autoComplete="off"
                />
              </div>
              <div className="admin-field">
                <label htmlFor="admin-new-password">Password</label>
                <input
                  id="admin-new-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  disabled={provisionMutation.isPending}
                  data-testid="provision-password-input"
                  autoComplete="new-password"
                />
              </div>
              <div className="admin-field">
                <label htmlFor="admin-new-role">Role</label>
                <select
                  id="admin-new-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as ProvisionRole)}
                  disabled={provisionMutation.isPending}
                  data-testid="provision-role-select"
                >
                  {PROVISIONABLE_ROLES.map((r) => (
                    <option key={r.role} value={r.role}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                className="demo-continue admin-create-button"
                disabled={provisionMutation.isPending}
                data-testid="provision-create-button"
              >
                <Plus size={18} />
                {provisionMutation.isPending ? "Creating…" : "Create User"}
              </button>

              {notice && (
                <p
                  className={`admin-notice ${notice.kind === "success" ? "admin-notice--success" : "admin-notice--error"}`}
                  role="alert"
                  data-testid="provision-notice"
                >
                  {notice.text}
                </p>
              )}
            </form>
          </section>

          <section className="admin-panel admin-panel--status" data-testid="admin-status-panel">
            <div className="admin-panel-head">
              <span className="admin-panel-icon">
                <ServerCog size={18} />
              </span>
              <div>
                <h2>System status</h2>
                <p>Operational metadata only — no account secrets, no welfare data.</p>
              </div>
            </div>

            {statusFailed ? (
              <p className="admin-notice admin-notice--error" data-testid="status-error">
                Unable to load system status. Backend unavailable.
              </p>
            ) : !status ? (
              <p className="admin-status-loading" data-testid="status-loading">
                Loading status…
              </p>
            ) : (
              <div className="admin-status-grid" data-testid="status-chips">
                <div className="admin-status-chip">
                  <Database size={15} />
                  <span>
                    <small>Database</small>
                    <strong className={status.database.status === "ok" ? "admin-chip-ok" : "admin-chip-bad"}>
                      {status.database.status}
                    </strong>
                  </span>
                </div>
                <div className="admin-status-chip">
                  <ShieldCheck size={15} />
                  <span>
                    <small>Authentication</small>
                    <strong>{status.authentication.provider.toUpperCase()}</strong>
                  </span>
                </div>
                <div className="admin-status-chip">
                  <Users size={15} />
                  <span>
                    <small>Active accounts</small>
                    <strong>{status.authentication.active_accounts}</strong>
                  </span>
                </div>
                <div className="admin-status-chip">
                  <ServerCog size={15} />
                  <span>
                    <small>Model</small>
                    <strong className={status.model?.ready ? "admin-chip-ok" : "admin-chip-bad"}>
                      {status.model?.ready ? "READY" : "UNAVAILABLE"}
                    </strong>
                  </span>
                </div>
              </div>
            )}

            {status?.model?.ready && status.model.model_version && (
              <p className="admin-status-note">
                ML model {status.model.product_name ?? "loaded"} v{status.model.model_version} ·{" "}
                {status.model.feature_count ?? 0} features.
              </p>
            )}
          </section>
        </div>

        <footer className="admin-footer">
          <ShieldCheck size={15} />
          <span>
            ADMIN traffic is restricted by the backend; provisioning of ADMIN accounts is
            impossible through this surface, and no individual welfare data is exposed here.
          </span>
        </footer>
      </main>
    </div>
  );
}