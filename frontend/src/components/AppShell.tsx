import { Outlet, Link, useLocation } from "react-router-dom";
import { Activity, BrainCircuit, ChevronRight, Fingerprint, HeartHandshake, LogOut, Menu, ShieldCheck, Users, X } from "lucide-react";
import { useState } from "react";
import { getAuthData } from "@/lib/auth";
import { endSession } from "@/lib/session";

const navItems = [
  { path: "/officer", label: "Welfare command", icon: Activity },
  { path: "/personnel", label: "My welfare view", icon: HeartHandshake },
  { path: "/analysis", label: "AI analysis", icon: BrainCircuit },
  { path: "/interventions", label: "Intervention desk", icon: ShieldCheck },
  { path: "/ethics", label: "Privacy & ethics", icon: Fingerprint },
];

const ROLE_LABELS: Record<string, string> = {
  PERSONNEL: "Personnel",
  WELFARE_OFFICER: "Welfare Officer",
  COMMANDER: "Commander",
};

export default function AppShell() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const authData = getAuthData();
  const role = authData?.role ?? "WELFARE_OFFICER";
  const canSeeCommand = role !== "PERSONNEL";

  function signOut() {
    endSession("/login");
  }

  return (
    <div className="platform-shell">
      <aside className={`platform-sidebar ${open ? "platform-sidebar-open" : ""}`} data-testid="platform-sidebar">
        <Link to={canSeeCommand ? "/officer" : "/personnel"} className="platform-brand" data-testid="platform-brand"><div className="brand-symbol"><Fingerprint size={20} /></div><div><strong>Manobal<span>-AI</span></strong><small>Welfare Signal</small></div></Link>
        <button className="sidebar-close" onClick={() => setOpen(false)} aria-label="Close menu" data-testid="sidebar-close-button"><X size={18} /></button>
        <div className="demo-label"><span className="demo-pip" /> DEMO DATA · SYNTHETIC RECORDS</div>
        <div className="nav-heading">Workspace</div>
        <nav className="platform-nav" aria-label="Workspace navigation">
          {navItems.filter((item) => canSeeCommand || item.path !== "/officer").map((item) => { const Icon = item.icon; const active = location.pathname === item.path || (item.path === "/personnel" && location.pathname.startsWith("/personnel/")); return <Link key={item.path} to={item.path} onClick={() => setOpen(false)} className={`platform-nav-link ${active ? "platform-nav-active" : ""}`} data-testid={`nav-${item.label.toLowerCase().replaceAll(" ", "-")}-link`}><Icon size={16} /><span>{item.label}</span>{active && <ChevronRight size={13} />}</Link>; })}
        </nav>
        <div className="sidebar-bottom"><div className="demo-role"><div className="role-avatar"><Users size={14} /></div><div><small>Signed in as</small><strong>{ROLE_LABELS[role]}</strong></div></div><button className="logout-icon" onClick={signOut} title="Exit demo" data-testid="demo-sign-out-button"><LogOut size={15} /></button></div>
      </aside>
      {open && <button className="sidebar-backdrop" onClick={() => setOpen(false)} aria-label="Close menu overlay" data-testid="sidebar-backdrop" />}
      <main className="platform-main">
        <header className="platform-topbar" data-testid="platform-topbar"><button className="sidebar-menu" onClick={() => setOpen(true)} aria-label="Open menu" data-testid="sidebar-menu-button"><Menu size={19} /></button><div className="platform-crumb"><span>Manobal-AI</span><ChevronRight size={13} /><strong>{location.pathname === "/officer" ? "Welfare command" : location.pathname.includes("personnel") ? "Personnel welfare" : location.pathname.replace("/", "") || "Workspace"}</strong></div><div className="topbar-right"><span className="live-status"><i /> Model gateway online</span><span className="demo-chip">DEMO MODE</span><div className="top-avatar">WO</div></div></header>
        <Outlet />
      </main>
    </div>
  );
}