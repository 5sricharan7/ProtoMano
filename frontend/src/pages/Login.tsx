import { useState } from "react";
import type { ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, Check, Fingerprint, HeartHandshake, ShieldCheck, Users } from "lucide-react";
import { apiPost } from "@/lib/api";
import { HERO_BACKGROUND_URL } from "@/lib/config";
import { setDemoRole, type DemoRole, ROLE_LABELS } from "@/lib/demo";
import type { DemoSeedResponse } from "@/lib/types";

const roles: { id: DemoRole; icon: ReactNode; note: string }[] = [
  { id: "personnel", icon: <Users size={25} />, note: "View your own wellness signals" },
  { id: "welfare-officer", icon: <HeartHandshake size={25} />, note: "Review people who need support" },
];

export default function Login() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<DemoRole>("welfare-officer");
  const seedMutation = useMutation({ mutationFn: () => apiPost<DemoSeedResponse>("/demo/seed", {}), onSuccess: () => { setDemoRole(selected); navigate(selected === "personnel" ? "/personnel" : "/officer"); } });

  return (
    <div className="reference-login">
      <header className="demo-header"><Link to="/" className="reference-brand" data-testid="login-brand-link"><span className="reference-brand-mark"><Fingerprint size={24} /></span><span><strong>Manobal<span>-AI</span></strong><small>Welfare Signal</small></span></Link><nav><Link to="/">Home</Link><Link to="/#how-it-works">How it works</Link><Link to="/#ethics">Privacy & ethics</Link></nav></header>
      <div className="demo-layout">
        <section className="demo-story" style={{ backgroundImage: `linear-gradient(90deg, rgba(0, 26, 23, .89), rgba(0, 26, 23, .30)), url(${HERO_BACKGROUND_URL})` }}><div><span className="demo-story-kicker">DEMO ENVIRONMENT</span><h1>Every signal<br /><em>deserves care.</em></h1><i className="demo-story-rule" /><p>Step into a synthetic welfare workspace built around the real uploaded model. No credentials. No external services. Just the full SIH story.</p></div><footer><span><ShieldCheck size={20} /> HUMAN-IN-THE-LOOP • WELFARE-ONLY PURPOSE</span><strong>People. Prepared. Protected.</strong></footer></section>
        <main className="demo-command"><div className="demo-command-inner"><span className="demo-command-kicker">Enter the command room</span><h2>Choose your<br /><em>demo perspective.</em></h2><p>Each role reveals a different part of the welfare journey.<br />All records are clearly synthetic.</p><div className="demo-role-list" data-testid="demo-role-list">{roles.map((role) => <button type="button" className={`demo-role-option ${selected === role.id ? "selected" : ""}`} key={role.id} onClick={() => setSelected(role.id)} data-testid={`role-${role.id}-button`}><span className="demo-role-icon">{role.icon}</span><span><strong>{ROLE_LABELS[role.id]}</strong><small>{role.note}</small></span><span className="demo-role-check">{selected === role.id && <Check size={17} />}</span></button>)}</div><button className="demo-continue" onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending} data-testid="enter-demo-button">{seedMutation.isPending ? "Preparing synthetic workspace…" : `Continue as ${ROLE_LABELS[selected]}`}<ArrowRight size={20} /></button>{seedMutation.isError && <p className="login-error" data-testid="login-error">Demo data could not be prepared. Please try again.</p>}<div className="demo-notice"><ShieldCheck size={19} /><span>Synthetic DEMO DATA is generated for presentation only. Risk results still come from the real `/api/predict` endpoint and uploaded LightGBM artifact.</span></div></div></main>
      </div>
    </div>
  );
}