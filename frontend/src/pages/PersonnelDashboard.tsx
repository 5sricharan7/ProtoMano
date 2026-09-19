import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BrainCircuit,
  CalendarDays,
  CheckCircle2,
  Clock3,
  HeartHandshake,
  HeartPulse,
  Info,
  MapPin,
  Minus,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { displayFeature, formatPercent, latestDemoHistory, riskTone } from "@/lib/demo";
import type {
  DemoPersonnel,
  ExplanationUnavailable,
  ExplanationFactor,
  InterventionAction,
  PredictionResponse,
  WelfareExplanationResponse,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import AIResultPanel from "@/components/AIResultPanel";

type FocusKey = "what-changed" | "why" | "context" | "support" | "ai";

const FOCUS_MODULES: { key: FocusKey; index: string; label: string; title: string; blurb: string; icon: typeof Activity }[] = [
  { key: "what-changed", index: "01", label: "What changed", title: "Recent trajectory", blurb: "How the signal has moved across stored snapshots.", icon: Activity },
  { key: "why", index: "02", label: "Why this signal", title: "Model contribution", blurb: "Ranked factors behind the current signal — contribution, not causation.", icon: ArrowUpRight },
  { key: "context", index: "03", label: "Recent context", title: "Welfare picture", blurb: "Weekly snapshots alongside current voluntary inputs.", icon: CalendarDays },
  { key: "support", index: "04", label: "Human support", title: "Welfare actions", blurb: "Interventions, follow-ups and recorded support.", icon: HeartHandshake },
  { key: "ai", index: "05", label: "AI assessment", title: "Live model analysis", blurb: "Run the deployed model against this record for context.", icon: BrainCircuit },
];

const TYPE_LABEL: Record<string, string> = {
  CHECK_IN: "Welfare check",
  COUNSELLING_REFERRAL: "Counselling referral",
  REST_RECOMMENDATION: "Rest recommendation",
  LEAVE_SUPPORT: "Leave support",
  MEDICAL_REFERRAL: "Medical referral",
  OTHER: "Other action",
};

const SUMMARIES: { key: string; label: string; icon: typeof Activity }[] = [
  { key: "workload", label: "Workload", icon: Activity },
  { key: "wellness", label: "Voluntary wellness", icon: HeartPulse },
  { key: "leave", label: "Leave access", icon: CalendarDays },
  { key: "deployment", label: "Posting context", icon: MapPin },
];

function signalVoice(band: string | undefined): string {
  if (band === "High") return "This signal should be reviewed promptly by a Welfare Officer in a private, voluntary conversation.";
  if (band === "Moderate") return "A voluntary, supportive check-in could help put recent changes into context.";
  if (band === "Low") return "Continue routine welfare touchpoints and keep your voluntary inputs current.";
  return "Complete a welfare assessment to establish a current signal.";
}

function formatDateTime(iso?: string): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return `${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}, ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
}

function formatDate(iso?: string): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("");
}

function supportTone(status: string): string {
  if (status === "OPEN") return "watch";
  if (status === "FOLLOW_UP") return "info";
  return "safe";
}

function isExplanationUnavailable(value: WelfareExplanationResponse | ExplanationUnavailable): value is ExplanationUnavailable {
  return (value as ExplanationUnavailable).status === "insufficient_data";
}

export default function PersonnelDashboard() {
  const { personnelId } = useParams();
  const [focus, setFocus] = useState<FocusKey>("what-changed");

  const query = useQuery({ queryKey: ["demo-personnel"], queryFn: () => apiGet<DemoPersonnel[]>("/demo/personnel"), retry: false });
  const profile = useMemo(() => {
    if (!personnelId) return null;
    return (query.data ?? []).find((item) => item.id === personnelId) ?? null;
  }, [personnelId, query.data]);

  const latest = profile ? latestDemoHistory(profile) : undefined;
  const prior = profile?.history.at(-2);
  const band = latest?.band ?? "Low";
  const tone = riskTone(band);
  const changePts = latest && prior ? Math.round((latest.probability - prior.probability) * 100) : null;
  const bandShift = latest && prior && latest.band !== prior.band ? `${prior.band} → ${latest.band}` : null;

  const explanationQuery = useQuery({
    queryKey: ["welfare-explanation", profile?.id],
    queryFn: () => {
      if (!profile) return Promise.resolve(null);
      return apiGet<WelfareExplanationResponse | ExplanationUnavailable>(`/personnel/${encodeURIComponent(profile.id)}/welfare-explanation`);
    },
    enabled: !!profile && focus === "why",
    retry: false,
  });

  const interventionsQuery = useQuery({
    queryKey: ["personnel-interventions", profile?.id],
    queryFn: () => {
      if (!profile) return Promise.resolve([] as InterventionAction[]);
      return apiGet<InterventionAction[]>(`/personnel/${encodeURIComponent(profile.id)}/interventions`);
    },
    enabled: !!profile && focus === "support",
    retry: false,
  });

  if (query.isLoading) {
    return (
      <MotionConfig reducedMotion="user">
        <div className="page-frame welfare-brief-page" data-testid="personnel-dashboard">
          <div className="welfare-seed-container">
            <Card className="seed-card loading-card">
              <Sparkles size={26} />
              <h2>Demo data is being prepared</h2>
              <p>Return to the role switch to load the synthetic presentation records.</p>
              <Link to="/login" className="text-link" data-testid="personnel-return-login-link">
                Return to demo entry <ArrowRight size={16} />
              </Link>
            </Card>
          </div>
        </div>
      </MotionConfig>
    );
  }

  if (query.isError) {
    return (
      <MotionConfig reducedMotion="user">
        <div className="page-frame welfare-brief-page" data-testid="personnel-dashboard">
          <div className="welfare-seed-container">
            <Card className="seed-card loading-card">
              <ShieldAlert size={26} />
              <h2>The demo records could not be loaded</h2>
              <p>The personnel record list is unavailable. No welfare view can be shown without a confirmed record.</p>
              <button type="button" className="brief-retry" onClick={() => query.refetch()}>
                Retry loading demo data
              </button>
            </Card>
          </div>
        </div>
      </MotionConfig>
    );
  }

  if (!personnelId) {
    return <SelectRecordState roster={query.data ?? []} />;
  }

  if (!profile) {
    return <MissingRecordState personnelId={personnelId} roster={query.data ?? []} />;
  }

  const explanation = explanationQuery.data;
  const interventions = interventionsQuery.data;

  function openLiveAssessment() {
    setFocus("ai");
    const rail = document.getElementById("personnel-focus-rail");
    rail?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="page-frame welfare-brief-page" data-testid="personnel-dashboard">
        <Link to="/officer" className="back-link" data-testid="profile-back-link">
          <ArrowLeft size={14} /> Back to welfare command
        </Link>

        <section className="brief-hero" data-testid="personnel-hero">
          <div className="brief-hero-copy">
            <span className="command-eyebrow">
              <span className="command-eyebrow-dot" /> My welfare view · private welfare workspace
            </span>
            <h1>
              Your welfare signal, <em>with context.</em>
            </h1>
            <p>This is a private, welfare-only view of voluntary and organizational signals. It is not a performance score or diagnosis.</p>
          </div>
          <div className="brief-identity">
            <div className={`brief-avatar brief-avatar-${tone}`}>{initials(profile.name)}</div>
            <div className="brief-identity-meta">
              <small>DEMO DATA · SYNTHETIC RECORD</small>
              <strong>{profile.name}</strong>
              <span>
                {profile.rank} · {profile.unit}
              </span>
            </div>
          </div>
        </section>

        <section className={`current-signal signal-${tone}`} data-testid="personnel-current-status">
          <div className="current-signal-copy">
            <span className="command-eyebrow">
              <span className="command-eyebrow-dot" /> Current state
            </span>
            <div className="signal-headline">
              <h2>{latest?.band ?? "Not assessed"}</h2>
              <span className={`risk-pill risk-pill-${tone}`}>
                {latest ? `${formatPercent(latest.probability)} · model probability` : "No stored assessment"}
              </span>
            </div>
            <p className="signal-voice">{signalVoice(latest?.band)}</p>
            <div className="signal-readouts" data-testid="personnel-data-reliability">
              <div className="signal-readout">
                <span>Fusion state</span>
                <strong>{latest?.fusion_state?.replaceAll("_", " ") ?? "Not stored"}</strong>
              </div>
              <div className="signal-readout">
                <span>Evidence trust</span>
                <strong>{latest?.trust_score != null ? `${Math.round(latest.trust_score)} / 100` : "Not stored"}</strong>
              </div>
              <div className="signal-readout">
                <span>Assessment recorded</span>
                <strong>{formatDateTime(latest?.assessed_at)}</strong>
              </div>
            </div>
            <div className="signal-actions">
              <button type="button" className="reference-primary-button compact" onClick={openLiveAssessment} data-testid="personnel-open-profile-link">
                Run AI assessment <ArrowRight size={16} />
              </button>
              <Link to={`/interventions?personnel=${encodeURIComponent(profile.id)}`} className="reference-source-button compact" data-testid="profile-intervention-link">
                Record welfare action
              </Link>
            </div>
          </div>
          <div className="signal-meter-wrap" data-testid="personnel-signal-meter">
            <div className="signal-meter">
              <span className="signal-meter-label">Signal level</span>
              <div className="signal-meter-track">
                <i className={`signal-meter-fill fill-${tone}`} style={{ width: `${Math.round((latest?.probability ?? 0) * 100)}%` }} />
                <i className="signal-meter-tick" style={{ left: "33%" }} />
                <i className="signal-meter-tick" style={{ left: "66%" }} />
              </div>
              <div className="signal-scale">
                <span>Low</span>
                <span>Moderate</span>
                <span>High</span>
              </div>
            </div>
            <p className="signal-meter-caption">
              <ShieldCheck size={12} /> AI-supported model signal · human decision remains
            </p>
          </div>
        </section>

        <section className="brief-inspect">
          <div className="inspect-rail" id="personnel-focus-rail" role="tablist" aria-label="Welfare brief focus" data-testid="personnel-focus-rail">
            {FOCUS_MODULES.map((module) => {
              const Icon = module.icon;
              const active = focus === module.key;
              return (
                <button
                  type="button"
                  key={module.key}
                  className={`inspect-item${active ? " active" : ""}`}
                  onClick={() => setFocus(module.key)}
                  aria-pressed={active}
                  role="tab"
                  aria-selected={active}
                  data-testid={`personnel-focus-${module.key}`}
                >
                  <span className="inspect-index">{module.index}</span>
                  <span className="inspect-item-body">
                    <span className="inspect-item-label">
                      <Icon size={13} /> {module.label}
                    </span>
                    <strong>{module.title}</strong>
                    <span className="inspect-item-blurb">{module.blurb}</span>
                  </span>
                  <span className="inspect-marker" aria-hidden="true" />
                </button>
              );
            })}
          </div>
          <div className="inspect-detail" role="tabpanel" data-testid="personnel-detail-panel">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={focus}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2, ease: [0.33, 1, 0.68, 1] }}
              >
                {focus === "what-changed" && <WhatChangedDetail profile={profile} changePts={changePts} bandShift={bandShift} />}
                {focus === "why" && (
                  <WhyDetail
                    tone={tone}
                    query={explanationQuery}
                    explanation={explanation}
                    onRetry={() => explanationQuery.refetch()}
                  />
                )}
                {focus === "context" && <ContextDetail profile={profile} />}
                {focus === "support" && (
                  <SupportDetail
                    profileId={profile.id}
                    interventions={interventions}
                    query={interventionsQuery}
                  />
                )}
                {focus === "ai" && <AiAssessmentDetail profile={profile} />}
              </motion.div>
            </AnimatePresence>
          </div>
        </section>

        <section className="human-link-strip">
          <div className="human-link-icon">
            <ShieldCheck size={20} />
          </div>
          <div className="human-link-copy">
            <strong>AI SUPPORTS THE ASSESSMENT</strong>
            <span>
              The Welfare Officer remains responsible for the final welfare decision. This signal is decision support for voluntary support — never a
              diagnosis, disciplinary input or automated action.
            </span>
          </div>
          <Link to="/ethics" className="text-link" data-testid="personnel-ethics-link">
            Privacy & ethics <ArrowRight size={13} />
          </Link>
        </section>
      </div>
    </MotionConfig>
  );
}

function RosterLinks({ roster }: { roster: DemoPersonnel[] }) {
  return (
    <div className="personnel-roster" data-testid="personnel-select-roster">
      {roster.map((person) => (
        <Link className="personnel-roster-row" to={`/personnel/${encodeURIComponent(person.id)}`} key={person.id} data-testid={`personnel-roster-${person.id}`}>
          <span className="personnel-roster-avatar">{initials(person.name)}</span>
          <span className="personnel-roster-meta">
            <strong>{person.name}</strong>
            <small>
              {person.rank} · {person.unit} · {person.service_number}
            </small>
          </span>
          <ArrowRight className="personnel-roster-arrow" size={14} />
        </Link>
      ))}
    </div>
  );
}

function SelectRecordState({ roster }: { roster: DemoPersonnel[] }) {
  return (
    <MotionConfig reducedMotion="user">
      <div className="page-frame welfare-brief-page" data-testid="personnel-dashboard">
        <div className="personnel-select-state">
          <div className="personnel-select-card" data-testid="personnel-select-card">
            <span className="command-eyebrow">
              <span className="command-eyebrow-dot" /> My welfare view · private welfare workspace
            </span>
            <h1>
              Select a personnel record.
            </h1>
            <p className="personnel-select-lede">
              Every welfare view is private and record-specific. Choose the synthetic record you want to inspect — details stay hidden until a
              record is confirmed.
            </p>
            {roster.length ? (
              <RosterLinks roster={roster} />
            ) : (
              <p className="personnel-select-none">No demo records are available to select.</p>
            )}
            <Link to="/officer" className="text-link" data-testid="personnel-go-command-link">
              Go to welfare command <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </div>
    </MotionConfig>
  );
}

function MissingRecordState({ personnelId, roster }: { personnelId: string; roster: DemoPersonnel[] }) {
  return (
    <MotionConfig reducedMotion="user">
      <div className="page-frame welfare-brief-page" data-testid="personnel-dashboard">
        <div className="personnel-select-state">
          <div className="personnel-select-card" data-testid="personnel-missing-card">
            <span className="command-eyebrow">
              <span className="command-eyebrow-dot" /> My welfare view · private welfare workspace
            </span>
            <h1>Record not found.</h1>
            <p className="personnel-select-lede">
              “{personnelId}” is not in the loaded demo record list. No welfare view is shown until a valid record is selected.
            </p>
            {roster.length ? <RosterLinks roster={roster} /> : null}
            <Link to="/officer" className="text-link" data-testid="personnel-go-command-link">
              Go to welfare command <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </div>
    </MotionConfig>
  );
}

function DetailHead({ index, title, sub }: { index: string; title: string; sub?: string }) {
  return (
    <div className="brief-detail-head">
      <div>
        <span className="brief-module-index">{index}</span>
        <h3>{title}</h3>
        {sub ? <span className="detail-sub">{sub}</span> : null}
      </div>
    </div>
  );
}

function BriefNote({ children }: { children: ReactNode }) {
  return (
    <p className="brief-note">
      <Info size={12} /> {children}
    </p>
  );
}

function UnavailableBlock({ title, reason }: { title: string; reason: string }) {
  return (
    <div className="brief-unavailable" role="status">
      <Info size={16} />
      <div>
        <strong>{title}</strong>
        <span>{reason}</span>
      </div>
    </div>
  );
}

function WhatChangedDetail({ profile, changePts, bandShift }: { profile: DemoPersonnel; changePts: number | null; bandShift: string | null }) {
  if (!profile.history.length) {
    return <UnavailableBlock title="Not enough assessment history" reason="No stored snapshots are available for this record." />;
  }
  if (profile.history.length < 2) {
    return (
      <>
        <DetailHead index="01" title="Latest signal level" sub="One stored snapshot" />
        <div className="single-signal-line">
          <span className={`trajectory-band band-${riskTone(profile.history[0].band)}`}>{profile.history[0].band}</span>
          <strong>{formatPercent(profile.history[0].probability)}</strong>
          <small>{formatDate(profile.history[0].assessed_at)}</small>
        </div>
        <UnavailableBlock title="No comparison available" reason="A second snapshot is needed to compare how the signal has moved." />
      </>
    );
  }
  const latest = profile.history[profile.history.length - 1];
  const prior = profile.history[profile.history.length - 2];
  const deltaClass = changePts === null ? "stable" : changePts > 0 ? "rising" : changePts < 0 ? "falling" : "stable";
  return (
    <>
      <div className="brief-detail-head">
        <div>
          <span className="brief-module-index">01</span>
          <h3>Signal over stored snapshots</h3>
          <span className="detail-sub">Latest vs. prior stored assessment</span>
        </div>
        <span className={`trajectory-change ${deltaClass}`}>
          {changePts === null ? <Minus size={13} /> : changePts > 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
          {changePts !== null ? `${changePts > 0 ? "+" : ""}${changePts} pts` : "No comparison"}
          {bandShift ? ` · ${bandShift}` : ""}
        </span>
      </div>
      <div className="trajectory-bars">
        {profile.history.map((point, index) => (
          <div className="trajectory-bar-item" key={`${point.assessed_at}-${index}`}>
            <span className="trajectory-value">{formatPercent(point.probability)}</span>
            <div className="trajectory-track">
              <i className={`trajectory-fill fill-${riskTone(point.band)}`} style={{ height: `${Math.max(14, point.probability * 100)}%` }} />
            </div>
            <small className="trajectory-date">{formatDate(point.assessed_at)}</small>
            <strong className={`trajectory-band band-${riskTone(point.band)}`}>{point.band}</strong>
          </div>
        ))}
      </div>
      {prior && latest && (
        <div className="signal-compare">
          <span>
            Prior snapshot: <strong>{prior.band}</strong> at <strong>{formatPercent(prior.probability)}</strong>
          </span>
          <span>
            Latest snapshot: <strong>{latest.band}</strong> at <strong>{formatPercent(latest.probability)}</strong>
          </span>
        </div>
      )}
      <BriefNote>
        Differences come only from stored model assessments, shown chronologically. A trend is context, not a diagnosis.
      </BriefNote>
    </>
  );
}

function ErrorBlock({ title, message, onRetry, cta }: { title: string; message: string; onRetry?: () => void; cta?: ReactNode }) {
  return (
    <div className="brief-unavailable" role="alert">
      <ShieldAlert size={16} />
      <div>
        <strong>{title}</strong>
        <span>{message}</span>
        {onRetry ? (
          <button type="button" className="brief-retry" onClick={onRetry} data-testid="personnel-why-retry">
            Retry
          </button>
        ) : null}
        {cta ? <div className="brief-unavailable-cta">{cta}</div> : null}
      </div>
    </div>
  );
}

function WhyDetail({
  tone,
  query,
  explanation,
  onRetry,
}: {
  tone: string;
  query: { isLoading: boolean; isError: boolean; error: Error | null };
  explanation: WelfareExplanationResponse | ExplanationUnavailable | null | undefined;
  onRetry: () => void;
}) {
  if (query.isLoading) {
    return (
      <div className="brief-loading" role="status">
        <Activity size={16} />
        <div>
          <strong>Compiling model explanation</strong>
          <span>Reading the stored four-week window and model contributions.</span>
        </div>
      </div>
    );
  }
  if (query.isError) {
    const error = query.error;
    const status = error instanceof ApiError ? error.status : null;
    const message =
      status === 503
        ? "Model-backed explanation is temporarily unavailable. The stored signal is unchanged."
        : status === 401 || status === 403
          ? "Your session role does not have access to model explanations for this record."
          : "The explanation could not be produced from the stored data.";
    return <ErrorBlock title="Explanation unavailable" message={message} onRetry={onRetry} />;
  }
  if (!explanation) return null;
  if (isExplanationUnavailable(explanation)) {
    return <UnavailableBlock title="Not enough assessment history" reason={explanation.message || explanation.reason} />;
  }
  if (explanation.explanation_status === "explanation_unavailable") {
    return <UnavailableBlock title="Explanation unavailable" reason={explanation.status_message} />;
  }
  return (
    <>
      <div className="brief-detail-head">
        <div>
          <span className="brief-module-index">02</span>
          <h3>Ranked contributing factors</h3>
          <span className="detail-sub">Model contribution — not causation</span>
        </div>
        <span className={`risk-pill risk-pill-${tone}`}>
          {explanation.prediction.predicted_band} · {formatPercent(explanation.prediction.risk_probability)}
        </span>
      </div>
      <div className="factor-list">
        {explanation.top_contributing_factors.map((factor, index) => (
          <FactorRow key={factor.feature} factor={factor} index={index + 1} />
        ))}
      </div>
      <BriefNote>
        {explanation.what_changed.status === "available"
          ? `Compared against the prior observed period: ${explanation.what_changed.basis}`
          : "Factor contributions come from the deployed model. Absent data is never shown as improvement or deterioration."}
      </BriefNote>
    </>
  );
}

function FactorRow({ factor, index }: { factor: ExplanationFactor; index: number }) {
  const up = factor.direction === "increases";
  const down = factor.direction === "decreases";
  const width = Math.min(100, Math.max(9, Math.abs(factor.contribution) * 2.5));
  const Icon = up ? ArrowUpRight : down ? ArrowDownRight : Minus;
  const label = up ? "Raises signal" : down ? "Lowers signal" : "Neutral";
  return (
    <div className="factor-row" data-testid={`explanation-factor-${factor.feature}`}>
      <span className="factor-rank">{String(index).padStart(2, "0")}</span>
      <div className="factor-body">
        <div className="factor-label">
          <strong>{factor.display_name}</strong>
          <span className={`factor-direction ${up ? "direction-up" : down ? "direction-down" : "direction-neutral"}`}>
            <Icon size={13} /> {label}
          </span>
        </div>
        <div className="factor-track">
          <i className={`factor-fill ${up ? "fill-up" : down ? "fill-down" : "fill-neutral"}`} style={{ width: `${width}%` }} />
        </div>
      </div>
      <span className="factor-value">{factor.contribution > 0 ? "+" : ""}{factor.contribution.toFixed(2)}</span>
    </div>
  );
}

function ContextDetail({ profile }: { profile: DemoPersonnel }) {
  return (
    <>
      <DetailHead index="03" title="Recent welfare picture" sub="Stored snapshots and current inputs" />
      {profile.history.length ? (
        <div className="week-line">
          {profile.history.map((point, index) => (
            <div className="week-tick" key={`${point.assessed_at}-${index}`}>
              <span className="week-date">{formatDate(point.assessed_at)}</span>
              <div className="week-node">
                <i className={`week-ring ring-${riskTone(point.band)}`} />
                <div className="week-track">
                  <i className={`week-fill fill-${riskTone(point.band)}`} style={{ width: `${Math.round(point.probability * 100)}%` }} />
                </div>
                <strong className={`week-band band-${riskTone(point.band)}`}>{point.band}</strong>
                <span className="week-prob">{formatPercent(point.probability)}</span>
                {point.trust_score != null ? <small className="week-trust">Trust {Math.round(point.trust_score)}</small> : null}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <UnavailableBlock title="Not enough assessment history" reason="No stored snapshots are available to build a weekly picture." />
      )}
      <div className="context-summary">
        <span className="context-heading">Current inputs</span>
        <div className="context-summary-grid">
          {SUMMARIES.map((item) => {
            const Icon = item.icon;
            const value = profile.summary[item.key] ?? "—";
            return (
              <div className="context-summary-chip" key={item.key} data-testid={`personnel-context-${item.key}`}>
                <Icon size={14} />
                <div data-testid={`profile-${item.key}-indicator`}>
                  <small>{item.label}</small>
                  <strong>{value}</strong>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <BriefNote>Snapshots are the stored weekly model assessments; inputs are the current record values associated with this profile.</BriefNote>
    </>
  );
}

function SupportDetail({
  profileId,
  interventions,
  query,
}: {
  profileId: string;
  interventions: InterventionAction[] | undefined;
  query: { isLoading: boolean; isError: boolean };
}) {
  const deskLink = (
    <Link to={`/interventions?personnel=${encodeURIComponent(profileId)}`} className="outlined-link" data-testid="personnel-intervention-link">
      Open intervention desk <ArrowRight size={14} />
    </Link>
  );
  if (query.isLoading) {
    return (
      <div className="brief-loading" role="status">
        <HeartHandshake size={16} />
        <div>
          <strong>Loading welfare actions</strong>
          <span>Reading the recorded support history for this record.</span>
        </div>
      </div>
    );
  }
  if (query.isError) {
    return (
      <ErrorBlock
        title="Support history unavailable"
        message="The recorded welfare actions for this record could not be loaded. You can still open the intervention desk."
        cta={deskLink}
      />
    );
  }
  if (!interventions || interventions.length === 0) {
    return (
      <>
        <DetailHead index="04" title="Welfare actions" sub="Interventions and follow-up history" />
        <div className="brief-unavailable">
          <HeartHandshake size={16} />
          <div>
            <strong>No welfare actions recorded yet</strong>
            <span>Nobody has recorded an intervention for this record. A Welfare Officer can start the human support trail here.</span>
          </div>
        </div>
        <div className="support-empty-cta">{deskLink}</div>
      </>
    );
  }
  return (
    <>
      <DetailHead index="04" title="Welfare actions" sub="Interventions and follow-up history" />
      <div className="support-timeline">
        {interventions.map((item) => {
          const t = supportTone(item.status);
          return (
            <div className="support-event" key={item.intervention_id} data-testid={`personnel-support-${item.intervention_id}`}>
              <div className="support-rail" aria-hidden="true">
                <i className={`support-node node-${t}`} />
                <span className="support-line" />
              </div>
              <div className="support-card">
                <div className="support-head">
                  <strong>{TYPE_LABEL[item.intervention_type] ?? item.intervention_type}</strong>
                  <span className={`support-status status-${t}`}>{item.status.replaceAll("_", " ")}</span>
                </div>
                <p>{item.reason ?? item.notes}</p>
                <div className="support-meta">
                  <Clock3 size={11} /> Recorded {formatDateTime(item.created_at)}
                  {item.follow_up_at ? (
                    <>
                      <span className="intelligence-sep">·</span> Follow-up {formatDate(item.follow_up_at)}
                    </>
                  ) : null}
                </div>
                {item.outcome ? (
                  <div className="support-outcome">
                    <CheckCircle2 size={12} /> {item.outcome}
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
      <div className="support-empty-cta">{deskLink}</div>
    </>
  );
}

function AiAssessmentDetail({ profile }: { profile: DemoPersonnel }) {
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const analysisMutation = useMutation({
    mutationFn: () => apiPost<PredictionResponse>("/predict", { personnel_id: profile.id, raw_records: profile.raw_records }),
    onSuccess: setResult,
  });
  return (
    <div className="intel-module ai-module">
      <div className="intel-module-head">
        <div>
          <span className="brief-module-index">05</span>
          <h3>AI assessment</h3>
          <span className="detail-sub">Run the deployed model against this record</span>
        </div>
        <Button
          className="analysis-button"
          onClick={() => analysisMutation.mutate()}
          disabled={analysisMutation.isPending}
          data-testid="run-profile-analysis-button"
        >
          <BrainCircuit size={16} />
          {analysisMutation.isPending ? "Running real inference…" : result ? "Refresh AI analysis" : "Run AI analysis"}
          <ArrowRight size={15} />
        </Button>
      </div>
      <div className="human-review-strip" data-testid="human-review-callout">
        <ShieldAlert size={18} />
        <div>
          <strong>AI ASSESSMENT — HUMAN REVIEW REQUIRED</strong>
          <span>This signal is decision support for voluntary welfare follow-up. It is never a diagnosis, disciplinary input or automated action.</span>
        </div>
      </div>
      {result ? (
        <>
          <AIResultPanel result={result} />
          <Card className="changed-card" data-testid="what-changed-card">
            <div className="card-title-row">
              <div>
                <span className="eyebrow-label">What changed?</span>
                <h2>Current vs. recent history</h2>
                <p>Only stored feature differences are shown. No causal claim is made.</p>
              </div>
              <BarChart3 size={17} />
            </div>
            {result.what_changed?.length ? (
              <div className="change-list">
                {result.what_changed.map((change) => (
                  <div className="change-row" key={change.feature}>
                    <div>
                      <strong>{displayFeature(change.feature)}</strong>
                      <span>
                        {change.previous.toFixed(1)} <ArrowRight size={11} /> {change.current.toFixed(1)}
                      </span>
                    </div>
                    <b className={change.delta > 0 ? "change-up" : "change-down"}>{change.delta > 0 ? "+" : ""}
                      {change.delta.toFixed(1)}</b>
                  </div>
                ))}
              </div>
            ) : (
              <div className="unavailable-note">
                <Info size={14} /> No previous assessment is available for comparison.
              </div>
            )}
          </Card>
          <Card className="trajectory-card" data-testid="risk-trajectory-card">
            <div className="card-title-row">
              <div>
                <span className="eyebrow-label">Risk trajectory</span>
                <h2>Signal over time</h2>
              </div>
              <Clock3 size={17} />
            </div>
            <div className="trajectory-chart">
              {result.trajectory.map((point, index) => (
                <div className="trajectory-point" key={`${point.assessed_at}-${index}`}>
                  <div className={`trajectory-bar bar-${riskTone(point.band)}`} style={{ height: `${Math.max(20, point.probability * 100)}%` }}>
                    <span>{formatPercent(point.probability)}</span>
                  </div>
                  <small>{new Date(point.assessed_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</small>
                  <strong>{point.band}</strong>
                </div>
              ))}
            </div>
            <p className="chart-footnote">
              <Info size={12} /> Derived from stored assessments; not an additional trajectory model.
            </p>
          </Card>
        </>
      ) : (
        <Card className="analysis-placeholder">
          <div className="analysis-placeholder-icon">
            <BrainCircuit size={25} />
          </div>
          <span className="eyebrow-label">Ready for live analysis</span>
          <h2>
            See the signal.
            <br />
            <em>Understand the person.</em>
          </h2>
          <p>
            Run the uploaded LightGBM model against this synthetic record to reveal calibrated risk, why it moved and what a welfare officer can
            do next.
          </p>
          <Button onClick={() => analysisMutation.mutate()} disabled={analysisMutation.isPending} data-testid="run-analysis-placeholder-button">
            Analyze this personnel record <ArrowRight size={15} />
          </Button>
        </Card>
      )}
    </div>
  );
}