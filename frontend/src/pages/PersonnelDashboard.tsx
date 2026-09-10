import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  HeartHandshake,
  HeartPulse,
  Info,
  LockKeyhole,
  MapPin,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import { apiGet } from "@/lib/api";
import { formatPercent, latestDemoHistory, riskTone } from "@/lib/demo";
import type { DemoPersonnel } from "@/lib/types";
import { Card } from "@/components/ui/card";

export default function PersonnelDashboard() {
  const query = useQuery({ queryKey: ["demo-personnel"], queryFn: () => apiGet<DemoPersonnel[]>("/demo/personnel"), retry: false });
  const profile = query.data?.[0];
  const latest = profile ? latestDemoHistory(profile) : undefined;
  const previous = profile?.history.at(-2);
  const probabilityChange = latest && previous ? latest.probability - previous.probability : null;
  const tone = riskTone(latest?.band ?? "Low");

  if (!profile) {
    return <div className="page-frame"><Card className="loading-card"><Sparkles size={26} /><h2>Demo data is being prepared</h2><p>Return to the role switch to load the synthetic presentation records.</p><Link to="/login" className="text-link" data-testid="personnel-return-login-link">Return to demo entry <ArrowRight size={16} /></Link></Card></div>;
  }

  return (
    <div className="page-frame personal-welfare-page" data-testid="personnel-dashboard">
      <header className="personal-welfare-header">
        <div><span className="eyebrow-label"><span className="step-index">PERSONNEL VIEW</span> Private welfare workspace</span><h1>Your welfare signal,<br /><em>with context.</em></h1><p>This is a private, welfare-only view of voluntary and organizational signals. It is not a performance score or diagnosis.</p></div>
        <div className="personal-person"><div className={`profile-avatar profile-avatar-${tone}`}>{profile.name.split(" ").map((part) => part[0]).join("")}</div><div><small>DEMO DATA · SYNTHETIC RECORD</small><strong>{profile.name}</strong><span>{profile.rank} · {profile.unit}</span></div></div>
      </header>

      <section className="personal-status-layout">
        <article className={`personal-status-hero status-${tone}`} data-testid="personnel-current-status">
          <div className="personal-status-copy"><span className="small-label">Current welfare signal</span><div className="personal-band-row"><h2>{latest?.band ?? "Not assessed"}</h2><span><i /> Human context required</span></div><p>{latest?.band === "High" ? "A welfare officer should review this signal with you privately and voluntarily." : latest?.band === "Moderate" ? "A supportive check-in may help put recent changes into context." : "Continue routine welfare touchpoints and keep your voluntary inputs current."}</p><Link to={`/personnel/${profile.id}`} className="reference-primary-button compact" data-testid="personnel-open-profile-link">View full assessment <ArrowRight size={18} /></Link></div>
          <div className="personal-score"><strong>{latest ? formatPercent(latest.probability) : "—"}</strong><span>model probability</span><small>Latest stored assessment</small></div>
        </article>

        <article className="personal-trust-card" data-testid="personnel-data-reliability"><div className="personal-trust-icon"><ShieldCheck size={23} /></div><span className="small-label">Data reliability</span><strong>{latest?.trust_score ?? "44 / 44"}</strong><p>{latest?.trust_score ? "Heuristic trust score — separate from model confidence." : "Complete feature profile available for the latest stored assessment."}</p><div className="trust-meter"><i style={{ width: `${latest?.trust_score ?? 100}%` }} /></div></article>
      </section>

      <section className="personal-detail-grid">
        <article className="personal-trajectory-panel" data-testid="personnel-risk-trajectory"><div className="personal-panel-heading"><div><span className="eyebrow-label">Recent trajectory</span><h2>How the signal has moved</h2></div>{probabilityChange !== null && <span className={probabilityChange > 0 ? "trajectory-change rising" : "trajectory-change falling"}>{probabilityChange > 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}{probabilityChange > 0 ? "+" : ""}{Math.round(probabilityChange * 100)} pts</span>}</div><div className="personal-trajectory-chart">{profile.history.map((point, index) => <div className="personal-chart-point" key={`${point.assessed_at}-${index}`}><span>{formatPercent(point.probability)}</span><div><i className={`point-${riskTone(point.band)}`} style={{ height: `${Math.max(18, point.probability * 100)}%` }} /></div><small>{new Date(point.assessed_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</small></div>)}</div><p className="personal-chart-note"><Info size={14} /> Stored model assessments shown chronologically. A trend is context, not a diagnosis.</p></article>

        <article className="personal-indicators-panel"><div className="personal-panel-heading"><div><span className="eyebrow-label">Available indicators</span><h2>What the assessment can see</h2></div><HeartPulse size={21} /></div><div className="personal-indicator-grid"><PersonalIndicator icon={<HeartPulse size={19} />} label="Voluntary wellness" value={profile.summary.wellness} /><PersonalIndicator icon={<Clock3 size={19} />} label="Workload" value={profile.summary.workload} /><PersonalIndicator icon={<CalendarDays size={19} />} label="Leave access" value={profile.summary.leave} /><PersonalIndicator icon={<MapPin size={19} />} label="Posting context" value={profile.summary.deployment} /></div></article>
      </section>

      <section className="personal-action-row">
        <article className="personal-next-step"><div className="next-step-icon"><HeartHandshake size={24} /></div><div><span className="eyebrow-label">Recommended next human step</span><h2>{latest?.band === "High" ? "A private welfare review" : latest?.band === "Moderate" ? "A voluntary supportive check-in" : "Continue routine welfare contact"}</h2><p>Recommendations are welfare-support rules reviewed by a person — not automatic model decisions.</p></div><Link to={`/personnel/${profile.id}`} className="outlined-link">See explanation <ArrowRight size={15} /></Link></article>
        <article className="personal-privacy-note"><LockKeyhole size={21} /><div><strong>Your context stays human.</strong><span>No automated disciplinary decision is made from this data.</span></div><Link to="/ethics" data-testid="personnel-ethics-link">Privacy & ethics <ArrowRight size={14} /></Link></article>
      </section>
    </div>
  );
}

function PersonalIndicator({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="personal-indicator"><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div><CheckCircle2 size={15} /></div>;
}