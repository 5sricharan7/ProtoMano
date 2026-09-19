import { Outlet, Link, useLocation, Navigate } from "react-router-dom";
import { Activity, BrainCircuit, ChevronRight, Fingerprint, HeartHandshake, LogOut, Menu, ShieldCheck, Users, X } from "lucide-react";
import { useState } from "react";
import { getAuthData } from "@/lib/auth";
import { endSession } from "@/lib/session";

const ROLE_LABELS: Record<string, string> = {
  PERSONNEL: "Personnel",
  WELFARE_OFFICER: "Welfare Officer",
  COMMANDER: "Commander",
};

const ROLE_HOMES: Record<string, string> = {
  PERSONNEL: "/personnel",
  WELFARE_OFFICER: "/officer",
  COMMANDER: "/command",
};

const ROLE_AVATARS: Record<string, string> = {
  PERSONNEL: "P",
  WELFARE_OFFICER: "WO",
  COMMANDER: "C",
};

const OFFICER_NAV = [
  { path: "/officer", label: "Welfare command", icon: Activity },
  { path: "/personnel", label: "My welfare view", icon: HeartHandshake },
  { path: "/analysis", label: "AI analysis", icon: BrainCircuit },
  { path: "/interventions", label: "Intervention desk", icon: ShieldCheck },
  { path: "/ethics", label: "Privacy & ethics", icon: Fingerprint },
];

const COMMANDER_NAV = [
  { path: "/command", label: "Commander workspace", icon: Activity },
  { path: "/analysis", label: "AI analysis", icon: BrainCircuit },
  { path: "/ethics", label: "Privacy & ethics", icon: Fingerprint },
];

const PERSONNEL_NAV = [
  { path: "/personnel", label: "My welfare view", icon: HeartHandshake },
  { path: "/analysis", label: "AI analysis", icon: BrainCircuit },
  { path: "/interventions", label: "Intervention desk", icon: ShieldCheck },
  { path: "/ethics", label: "Privacy & ethics", icon: Fingerprint },
];

const CRUMBS: Record<string, string> = {
  "/command": "Command",
  "/officer": "Welfare command",
  "/personnel": "Personnel welfare",
  "/analysis": "AI analysis",
  "/interventions": "Intervention desk",
  "/ethics": "Privacy & ethics",
};

export default function AppShell() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const authData = getAuthData();

  if (!authData) {
    return <Navigate to="/login" replace />;
  }

  const role = authData.role;
  const navItems = role === "COMMANDER" ? COMMANDER_NAV : role === "PERSONNEL" ? PERSONNEL_NAV : OFFICER_NAV;
  const homePath = ROLE_HOMES[role] ?? "/personnel";
  const crumb = CRUMBS[location.pathname] ?? (location.pathname.startsWith("/personnel/") ? "Personnel welfare" : location.pathname.replace("/", "") || "Workspace");

  function signOut() {
    endSession("/login");
  }

  return (
    <div className="platform-shell">
      <aside className={`platform-sidebar ${open ? "platform-sidebar-open" : ""}`} data-testid="platform-sidebar">
        <Link to={homePath} className="platform-brand" data-testid="platform-brand"><div className="brand-symbol"><Fingerprint size={20} /></div><div><strong>Manobal<span>-AI</span></strong><small>Welfare Signal</small></div></Link>
        <button className="sidebar-close" onClick={() => setOpen(false)} aria-label="Close menu" data-testid="sidebar-close-button"><X size={18} /></button>
        <div className="demo-label"><span className="demo-pip" /> DEMO DATA · SYNTHETIC RECORDS</div>
        <div className="nav-heading">Workspace</div>
        <nav className="platform-nav" aria-label="Workspace navigation">
          {navItems.map((item) => { const Icon = item.icon; const active = location.pathname === item.path || (item.path === "/personnel" && location.pathname.startsWith("/personnel/")); return <Link key={item.path} to={item.path} onClick={() => setOpen(false)} className={`platform-nav-link ${active ? "platform-nav-active" : ""}`} data-testid={`nav-${item.label.toLowerCase().replaceAll(" ", "-")}-link`}><Icon size={16} /><span>{item.label}</span>{active && <ChevronRight size={13} />}</Link>; })}
        </nav>
        <div className="sidebar-bottom"><div className="demo-role"><div className="role-avatar"><Users size={14} /></div><div><small>Signed in as</small><strong>{ROLE_LABELS[role]}</strong></div></div><button className="logout-icon" onClick={signOut} title="Exit demo" data-testid="demo-sign-out-button"><LogOut size={15} /></button></div>
      </aside>
      {open && <button className="sidebar-backdrop" onClick={() => setOpen(false)} aria-label="Close menu overlay" data-testid="sidebar-backdrop" />}
      <main className="platform-main">
        <header className="platform-topbar" data-testid="platform-topbar"><button className="sidebar-menu" onClick={() => setOpen(true)} aria-label="Open menu" data-testid="sidebar-menu-button"><Menu size={19} /></button><div className="platform-crumb"><span>Manobal-AI</span><ChevronRight size={13} /><strong>{crumb}</strong></div><div className="topbar-right"><span className="live-status"><i /> Model gateway online</span><span className="demo-chip">DEMO MODE</span><div className="top-avatar">{ROLE_AVATARS[role] ?? "?"}</div></div></header>
        <Outlet />
      </main>
    </div>
  );
}