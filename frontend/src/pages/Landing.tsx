import { useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CalendarDays,
  CheckCircle2,
  Eye,
  Fingerprint,
  HeartHandshake,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import { apiGet } from "@/lib/api";
import { GITHUB_REPOSITORY_URL, HERO_BACKGROUND_URL } from "@/lib/config";
import type { ModelInfo } from "@/lib/types";

const signalCategories = [
  { icon: Users, title: "Personnel data", count: "8 features", copy: "Basic information, duty patterns, location and behavior data." },
  { icon: CalendarDays, title: "Duty patterns", count: "10 features", copy: "Workload, shifts, deployments, leave and operational demands." },
  { icon: Activity, title: "Behavior", count: "8 features", copy: "Activity trends, engagement and routine changes." },
  { icon: HeartHandshake, title: "Wellness inputs", count: "8 features", copy: "Voluntary check-ins and self-reported wellness indicators." },
  { icon: CheckCircle2, title: "Other data", count: "10 features", copy: "Additional authorized organizational data sources." },
];

const flowSteps = [
  { icon: Users, title: "Personnel data", copy: "Basic information, duty patterns, location and behavior data already available with the officer." },
  { icon: BrainCircuit, title: "AI risk analysis", copy: "Our model detects unusual patterns and early signs of stress using multimodal data and trained signals." },
  { icon: Sparkles, title: "Early warning", copy: "The system flags potential risk levels with clear, actionable insights — not just numbers." },
  { icon: HeartHandshake, title: "Human support", copy: "Enables timely intervention, peer support and professional help when it matters most." },
];

const featureStrip = [
  { icon: BrainCircuit, title: "AI-powered prediction" },
  { icon: Eye, title: "Explainable by design" },
  { icon: HeartHandshake, title: "Welfare-first approach" },
  { icon: LockKeyhole, title: "Privacy & ethics" },
];

export default function Landing() {
  const [showFeatures, setShowFeatures] = useState(false);
  const modelQuery = useQuery({ queryKey: ["model-info"], queryFn: () => apiGet<ModelInfo>("/model-info"), retry: false });

  return (
    <div className="reference-landing">
      <header className="reference-header" data-testid="landing-navigation">
        <Link to="/" className="reference-brand" data-testid="landing-brand-link">
          <span className="reference-brand-mark"><Fingerprint size={24} /></span>
          <span><strong>Manobal<span>-AI</span></strong><small>Welfare Signal</small></span>
        </Link>
        <nav className="reference-nav" aria-label="Landing navigation">
          <a href="#how-it-works" data-testid="landing-how-link">How it works</a>
          <a href="#ethics" data-testid="landing-ethics-link">Privacy & ethics</a>
          <Link to="/login" className="reference-nav-cta" data-testid="landing-login-link">Enter demo <ArrowRight size={18} /></Link>
        </nav>
      </header>

      <main>
        <section
          className="reference-hero"
          style={{ backgroundImage: `linear-gradient(90deg, rgba(0, 24, 22, .98) 0%, rgba(0, 24, 22, .79) 33%, rgba(0, 24, 22, .15) 66%, rgba(0, 24, 22, .08) 100%), url(${HERO_BACKGROUND_URL})` }}
          data-testid="landing-hero"
        >
          <div className="reference-hero-copy">
            <div className="reference-kicker"><i /> HUMAN-CENTRED WELFARE INTELLIGENCE</div>
            <h1 data-testid="landing-hero-quote">They protect us every<br />day.<br /><em>Who protects their<br />well-being?</em></h1>
            <p data-testid="landing-subheading">Welfare Signal turns silent signs of stress into timely,<br />human support.</p>
            <div className="reference-hero-actions">
              <Link to="/login" className="reference-primary-button" data-testid="landing-enter-demo-button"><span className="button-symbol"><BrainCircuit size={23} /></span><span>Enter demo</span><ArrowRight size={20} /></Link>
              {GITHUB_REPOSITORY_URL ? (
                <a href={GITHUB_REPOSITORY_URL} target="_blank" rel="noreferrer" className="reference-source-button" data-testid="github-source-link"><svg className="github-mark" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.69c-2.78.6-3.37-1.18-3.37-1.18-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.9 1.53 2.35 1.09 2.92.83.09-.65.35-1.09.64-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.58 9.58 0 0 1 12 6.7c.85 0 1.71.11 2.51.34 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" /></svg><span><strong>View source code</strong><small>Access on GitHub</small></span></a>
              ) : null}
            </div>
          </div>
          <div className="reference-model-cards" data-testid="landing-hero-visual">
            <HeroSignalCard label="MODEL SIGNAL" title="Calibrated" detail="44 features • LightGBM" />
            <HeroSignalCard label="WELFARE STATUS" title="Stable" detail="Support not required" />
          </div>
        </section>

        <section className="reference-feature-band" data-testid="landing-trust-line">
          <FeatureBand icon={<HeartHandshake size={28} />} title="Welfare-first approach" copy="The output supports voluntary check-ins and trained human follow-up — not diagnosis, discipline or automation." />
          <FeatureBand icon={<ShieldCheck size={28} />} title="Privacy & ethics" copy="Role-aware workspaces, synthetic demo records and transparent model limitations keep people at the centre." />
          <FeatureBand icon={<Users size={28} />} title="Human judgement" copy="AI flags the risk. People provide the care." />
        </section>

        <section className="reference-section signal-path-section" id="how-it-works" data-testid="landing-how-it-works">
          <div className="reference-section-heading">
            <div className="reference-heading-copy"><span className="reference-section-index"><i />01 / The signal path</span><h2>From raw signals<br /><em>to human support.</em></h2><p>Manobal-AI connects the data an officer already holds with a clear next step—without pretending a model can replace a conversation.</p></div>
            <div className="signal-path-sketch" aria-hidden="true"><span>Personnel inputs</span><ArrowRight size={24} /><BrainCircuit size={42} /><ArrowRight size={24} /><span>Risk signal</span><ArrowRight size={24} /><HeartHandshake size={42} /></div>
          </div>
          <div className="reference-flow-grid">{flowSteps.map(({ icon: Icon, title, copy }, index) => <article className="reference-flow-card" key={title} data-testid={`flow-step-${index + 1}`}><span>0{index + 1}</span><div className="reference-flow-icon"><Icon size={27} /></div><h3>{title}</h3><p>{copy}</p>{index < flowSteps.length - 1 && <ArrowRight className="reference-flow-arrow" size={28} />}</article>)}</div>
        </section>

        <section className="reference-section trust-section" data-testid="landing-capabilities">
          <div className="trust-layout">
            <div className="reference-heading-copy trust-copy"><span className="reference-section-index"><i />02 / Built for trust</span><h2>Serious intelligence.<br /><em>Human judgement.</em></h2><p>A calibrated LightGBM model turns a precise 44-signal profile into an early welfare risk band.</p><Link to="/login" className="reference-primary-button compact" data-testid="trust-enter-demo-button">Enter demo <ArrowRight size={19} /></Link></div>
          <div className="signals-panel" data-testid="signals-panel"><div className="signals-panel-head"><div className="signal-wave-icon"><Activity size={32} /></div><div><h3>44 signals</h3><p>Organizational + voluntary wellness inputs</p></div><span><i /> Early signal</span></div><div className="signals-category-grid">{signalCategories.map(({ icon: Icon, title, count, copy }) => <article key={title}><div className="signals-category-icon"><Icon size={22} /></div><h4>{title}</h4><strong>({count})</strong><p>{copy}</p></article>)}</div><button className="features-toggle" type="button" disabled={!modelQuery.data} onClick={() => setShowFeatures((current) => !current)} aria-expanded={showFeatures} data-testid="view-all-features-button">{!modelQuery.data ? "Loading exact feature order…" : showFeatures ? "Hide feature list" : "View all 44 features"} <ArrowRight size={16} /></button>{showFeatures && modelQuery.data && <div className="expanded-feature-list" data-testid="expanded-feature-list">{modelQuery.data.feature_list_in_order.map((feature, index) => <span key={feature}><b>{String(index + 1).padStart(2, "0")}</b>{feature.replaceAll("__", " · ").replaceAll("_", " ")}</span>)}</div>}</div>
          </div>
          <div className="reference-capability-strip">{featureStrip.map(({ icon: Icon, title }) => <div key={title}><span><Icon size={23} /></span><strong>{title}</strong></div>)}</div>
        </section>

        <section className="reference-promise" id="ethics" data-testid="landing-ethics"><div><span className="reference-section-index"><i />03 / The promise</span><h2>Never a number<br /><em>without a person.</em></h2></div><div><p>Every risk band is a prompt for context, care and a trained welfare officer.<br />No automated disciplinary decisions. No clinical labels. No silent escalation.</p><Link to="/ethics" data-testid="landing-ethics-detail-link">Read our ethics position <ArrowRight size={17} /></Link></div></section>
      </main>
    </div>
  );
}

function HeroSignalCard({ label, title, detail }: { label: string; title: string; detail: string }) {
  return <div className="hero-signal-card"><span>{label}</span><div><i /><strong>{title}</strong><svg viewBox="0 0 95 24" aria-hidden="true"><path d="M1 16 C10 16, 10 5, 18 5 S28 20, 37 20 S47 7, 56 7 S67 18, 75 18 S84 4, 94 12" /></svg></div><small>{detail}</small></div>;
}

function FeatureBand({ icon, title, copy }: { icon: ReactNode; title: string; copy: string }) {
  return <article><span className="feature-band-icon">{icon}</span><div><h3>{title}</h3><p>{copy}</p></div></article>;
}