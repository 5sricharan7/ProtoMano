import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, ArrowRight, BrainCircuit, Clock3, Eye, MapPin, Minus, ShieldCheck, Sparkles, Target, TrendingDown, TrendingUp, User, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { apiGet, apiPost } from "@/lib/api";
import { formatPercent, latestDemoHistory, riskTone } from "@/lib/demo";
import type { DemoPersonnel, DemoSeedResponse, Overview } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const fetchDemo = () => apiGet<DemoPersonnel[]>("/demo/personnel");
const fetchOverview = () => apiGet<Overview>("/overview");
const EMPTY_PROFILES: DemoPersonnel[] = [];

type SignalTrajectory = "rising" | "falling" | "stable";

function signalTrajectory(profile: DemoPersonnel): SignalTrajectory {
  if (!profile.history || profile.history.length < 2) return "stable";
  const current = profile.history[profile.history.length - 1]?.probability ?? 0;
  const previous = profile.history[profile.history.length - 2]?.probability ?? 0;
  if (current > previous + 0.05) return "rising";
  if (current < previous - 0.05) return "falling";
  return "stable";
}

export default function OfficerDashboard() {
  const demoQuery = useQuery({ queryKey: ["demo-personnel"], queryFn: fetchDemo, retry: false });
  const overviewQuery = useQuery({ queryKey: ["overview"], queryFn: fetchOverview, retry: false });
  const seedMutation = useMutation({ mutationFn: () => apiPost<DemoSeedResponse>("/demo/seed", {}), onSuccess: () => demoQuery.refetch() });
  const profiles = demoQuery.data ?? EMPTY_PROFILES;
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<string | null>(null);
  const selectedRowRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!selectedPersonnelId && profiles.length > 0) {
      const fallback = profiles.find((p) => latestDemoHistory(p)?.band === "High")
        ?? profiles.find((p) => { const band = latestDemoHistory(p)?.band; return band === "High" || band === "Moderate"; })
        ?? profiles[0];
      setSelectedPersonnelId(fallback.id);
    }
  }, [profiles, selectedPersonnelId]);

  const needsAttention = profiles.filter((profile) => {
    const band = latestDemoHistory(profile)?.band;
    return band === "High" || band === "Moderate";
  });
  const selectedPersonnel = profiles.find((p) => p.id === selectedPersonnelId) || needsAttention[0] || profiles[0];

  if (profiles.length === 0) {
    return (
      <div className="page-frame officer-command-page" data-testid="officer-dashboard">
        <div className="command-seed-container">
          <Card className="seed-card">
            <Sparkles size={25} />
            <h2>Prepare the live demo workspace</h2>
            <p>Seed synthetic personnel histories. Every later assessment will use the real uploaded model.</p>
            <Button onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending} data-testid="seed-demo-data-button">
              {seedMutation.isPending ? "Preparing…" : "Load DEMO DATA"}<ArrowRight size={16} />
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="page-frame officer-command-page" data-testid="officer-dashboard">
      <MotionConfig reducedMotion="user">
        <div className="command-layout">
          <div className="command-sidebar">
            <CommandHero />
            <MetricRail
              personnelCount={profiles.length}
              assessmentsToday={overviewQuery.data?.assessments_today ?? 0}
              needsAttention={needsAttention.length}
              humanReviews={overviewQuery.data?.open_interventions ?? 0}
            />
            <CommandStatus isOnline={demoQuery.isSuccess} cohortCount={profiles.length} />
          </div>

          <div className="command-main">
            <PriorityQueue
              profiles={profiles}
              selectedId={selectedPersonnelId}
              onSelect={setSelectedPersonnelId}
              selectedRef={selectedRowRef}
            />
          </div>

          <div className="command-intelligence">
            <IntelligencePanel personnel={selectedPersonnel} panelRef={panelRef} />
          </div>

          <FocusConnector
            sourceRef={selectedRowRef}
            targetRef={panelRef}
            activeId={selectedPersonnelId}
          />
        </div>
      </MotionConfig>
    </div>
  );
}

function CommandHero() {
  return (
    <div className="command-hero">
      <svg className="command-hero-motif" viewBox="0 0 240 240" fill="none" aria-hidden="true">
        <circle cx="186" cy="54" r="40" stroke="currentColor" strokeOpacity="0.16" />
        <circle cx="186" cy="54" r="64" stroke="currentColor" strokeOpacity="0.09" />
        <circle cx="186" cy="54" r="90" stroke="currentColor" strokeOpacity="0.05" />
        <circle cx="186" cy="54" r="3" fill="currentColor" fillOpacity="0.35" />
        <path d="M 186 14 A 40 40 0 0 1 226 54" stroke="currentColor" strokeOpacity="0.3" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M 186 100 v6 M 180 54 h-6" stroke="currentColor" strokeOpacity="0.22" strokeWidth="1.2" strokeLinecap="round" />
        <path d="M 26 196 h36 M 26 176 h36 M 26 156 h24" stroke="currentColor" strokeOpacity="0.13" strokeWidth="1" strokeLinecap="round" />
        <path d="M 42 176 v20 M 62 196 v20" stroke="currentColor" strokeOpacity="0.13" strokeWidth="1" strokeLinecap="round" />
        <path d="M 10 228 L 230 228" stroke="currentColor" strokeOpacity="0.08" strokeWidth="1" />
      </svg>
      <span className="command-eyebrow">
        <span className="command-eyebrow-dot" />
        COMMAND 01
      </span>
      <h1>Welfare command center</h1>
      <span className="command-role">Welfare officer dashboard</span>
      <p className="command-subtitle">
        A calm operational view of the people behind the signals. Select a record to understand the why, the change and the next human step.
      </p>
      <div className="command-query">
        <span className="command-query-label">PRIMARY QUERY</span>
        <span className="command-query-text">Who needs attention?</span>
      </div>
      <div className="demo-data-indicator">
        <span className="demo-pip" />
        <span>DEMO DATA</span>
        <span className="demo-pip-sep">|</span>
        <span>Synthetic records</span>
      </div>
    </div>
  );
}

function MetricRail({ personnelCount, assessmentsToday, needsAttention, humanReviews }: { personnelCount: number; assessmentsToday: number; needsAttention: number; humanReviews: number }) {
  const metrics = [
    { label: "PERSONNEL", value: personnelCount, note: "demo records", icon: Users, tone: "mint", testId: "metric-personnel" },
    { label: "ASSESSMENTS", value: assessmentsToday, note: "assessments today", icon: BrainCircuit, tone: "amber", testId: "metric-assessments" },
    { label: "ATTENTION", value: needsAttention, note: "priority cases", icon: AlertTriangle, tone: "coral", testId: "metric-attention" },
    { label: "HUMAN REVIEWS", value: humanReviews, note: "intervention desk", icon: ShieldCheck, tone: "blue", testId: "metric-reviews" },
  ];

  return (
    <div className="metric-rail" data-testid="command-metrics">
      {metrics.map((metric, index) => (
        <motion.div
          key={metric.label}
          className={`metric-rail-item metric-${metric.tone}`}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.08 }}
          data-testid={metric.testId}
        >
          <div className="metric-rail-header">
            <metric.icon size={14} />
            <span>{metric.label}</span>
          </div>
          <div className="metric-rail-value">{metric.value}</div>
          <div className="metric-rail-note">{metric.note}</div>
        </motion.div>
      ))}
    </div>
  );
}

function CommandStatus({ isOnline, cohortCount }: { isOnline: boolean; cohortCount: number }) {
  return (
    <div className="command-status" data-testid="command-status">
      <div className="command-status-header">
        <span className="command-status-eyebrow">COMMAND STATUS</span>
        <span className={`status-indicator ${isOnline ? "status-safe" : "status-watch"}`}>
          <span className="status-dot" />
          {isOnline ? "Online" : "Checking"}
        </span>
      </div>
      <div className="status-info">
        <span className="status-label">Welfare signal service</span>
        <span className="status-state">{isOnline ? "Operational · assists officer review" : "Awaiting connection"}</span>
      </div>
      <div className="command-status-foot">
        <span className="status-foot-key">COHORT IN VIEW</span>
        <span className="status-foot-value">{cohortCount} personnel</span>
      </div>
      <Link to="/analysis" className="status-action" data-testid="open-analysis-link">
        <span>View intelligence pipeline</span>
        <ArrowRight size={12} />
      </Link>
    </div>
  );
}

function PriorityQueue({ profiles, selectedId, onSelect, selectedRef }: { profiles: DemoPersonnel[]; selectedId: string | null; onSelect: (id: string) => void; selectedRef: RefObject<HTMLDivElement | null> }) {
  const bandOrder = { High: 0, Moderate: 1, Low: 2 } as const;
  const sortedProfiles = [...profiles].sort((a, b) => {
    const bandA = (latestDemoHistory(a)?.band ?? "Low") as keyof typeof bandOrder;
    const bandB = (latestDemoHistory(b)?.band ?? "Low") as keyof typeof bandOrder;
    return bandOrder[bandA] - bandOrder[bandB];
  });

  const reviewCount = sortedProfiles.filter((p) => {
    const band = latestDemoHistory(p)?.band;
    return band === "High" || band === "Moderate";
  }).length;

  return (
    <div className="priority-queue" data-testid="priority-queue">
      <div className="queue-header">
        <div className="queue-header-row">
          <div>
            <span className="queue-eyebrow">PRIORITY QUEUE</span>
            <h2>Who needs attention?</h2>
          </div>
          <span className="queue-count">{reviewCount} {reviewCount === 1 ? "review" : "reviews"} needed</span>
        </div>
        <p className="queue-hint">
          Based on the latest stored model assessment for each demo record.
        </p>
      </div>

      <div className="queue-list" role="list">
        <AnimatePresence initial={false}>
          {sortedProfiles.map((profile, index) => {
            const history = latestDemoHistory(profile);
            const band = history?.band ?? "Low";
            const probability = history?.probability ?? 0;
            const isSelected = selectedId === profile.id;
            const workload = profile.summary?.workload;
            const trajectory = signalTrajectory(profile);

            return (
              <motion.div
                key={profile.id}
                ref={isSelected ? selectedRef : undefined}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                aria-label={`Inspect ${profile.name}, ${profile.rank}, ${band} assessment`}
                className={`queue-item queue-item-${riskTone(band)} ${isSelected ? "queue-item-selected" : ""}`}
                onClick={() => onSelect(profile.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(profile.id);
                  }
                }}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ x: 3 }}
                whileTap={{ scale: 0.995 }}
                data-testid={`queue-item-${profile.id}`}
              >
                <div className="queue-item-body">
                  <div className={`queue-avatar queue-avatar-${riskTone(band)}`}>
                    {profile.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                  </div>
                  <div className="queue-info">
                    <div className="queue-name">
                      <span>{profile.name}</span>
                      <span className="queue-rank">{profile.rank}</span>
                    </div>
                    <div className="queue-meta">
                      <span className="queue-unit">{profile.unit}</span>
                      <span className="queue-location">{profile.posting}</span>
                    </div>
                    {workload && (
                      <div className={`queue-signal queue-signal-${riskTone(band)}`}>
                        <Clock3 size={12} />
                        <span>{workload}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="queue-item-aside">
                  <span
                    className={`queue-trend queue-trend-${trajectory}`}
                    aria-label={`Trend ${trajectory} since last assessment`}
                    data-testid={`trend-${profile.id}`}
                  >
                    {trajectory === "rising" && <TrendingUp size={12} />}
                    {trajectory === "falling" && <TrendingDown size={12} />}
                    {trajectory === "stable" && <Minus size={12} />}
                  </span>
                  <div className={`queue-band queue-band-${riskTone(band)}`}>
                    <span className="band-label">{band}</span>
                    <span className="band-probability">{formatPercent(probability)}</span>
                  </div>
                  <Link
                    to={`/personnel/${profile.id}`}
                    className="queue-profile-link"
                    aria-label={`Open profile for ${profile.name}`}
                    data-testid={`profile-link-${profile.id}`}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Eye size={14} />
                    <span>Profile</span>
                  </Link>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

function IntelligencePanel({ personnel, panelRef }: { personnel: DemoPersonnel | undefined; panelRef: RefObject<HTMLDivElement | null> }) {
  if (!personnel) {
    return (
      <div className="intelligence-panel intelligence-empty" ref={panelRef} data-testid="intelligence-panel">
        <User size={24} />
        <span>Select a personnel record to view the welfare brief.</span>
      </div>
    );
  }

  const history = latestDemoHistory(personnel);
  const band = history?.band ?? "Low";
  const probability = history?.probability ?? 0;
  const trajectory = signalTrajectory(personnel);

  const summary = personnel.summary ?? {};
  const matterPoints = [
    summary.workload && `Workload signal — ${summary.workload}.`,
    summary.wellness && `Self-reported wellbeing — ${summary.wellness}.`,
    summary.leave && `Leave position — ${summary.leave}.`,
    summary.deployment && `Posting context — ${summary.deployment}.`,
  ].filter(Boolean) as string[];

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={personnel.id}
        ref={panelRef}
        className="intelligence-panel"
        role="region"
        aria-label={`Welfare brief for ${personnel.name}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        data-testid="intelligence-panel"
      >
        <div className="intelligence-header">
          <span className="intelligence-eyebrow">WELFARE BRIEF</span>
          <span className={`intelligence-status intelligence-status-${riskTone(band)}`}>
            {band.toUpperCase()}
          </span>
        </div>

        <div className="intelligence-personnel">
          <div className={`intelligence-avatar intelligence-avatar-${riskTone(band)}`}>
            {personnel.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
          </div>
          <div className="intelligence-identity">
            <h3>{personnel.name}</h3>
            <div className="intelligence-subtitle">
              <span>{personnel.rank}</span>
              <span className="intelligence-sep">·</span>
              <span>{personnel.unit}</span>
            </div>
            <div className="intelligence-location">
              <MapPin size={12} />
              {personnel.posting}
            </div>
          </div>
        </div>

        <div className="intelligence-assessment">
          <div className="section-kicker">
            <Target size={13} />
            <span>CURRENT ASSESSMENT</span>
          </div>
          <div className={`assessment-band assessment-band-${riskTone(band)}`}>
            <span className="band-value">{band}</span>
            <span className="band-percent">{formatPercent(probability)} risk probability</span>
          </div>
          <div className="risk-meter" aria-hidden="true">
            <span className={`risk-meter-fill risk-meter-fill-${riskTone(band)}`} style={{ width: `${Math.max(3, probability * 100)}%` }} />
          </div>
          <div className={`assessment-trajectory assessment-trajectory-${trajectory}`}>
            {trajectory === "rising" && <TrendingUp size={13} />}
            {trajectory === "falling" && <TrendingDown size={13} />}
            {trajectory === "stable" && <Minus size={13} />}
            <span>
              {trajectory === "rising" ? "Signal rising since last assessment"
                : trajectory === "falling" ? "Signal reducing since last assessment"
                : "Signal stable since last assessment"}
            </span>
          </div>
        </div>

        <div className="intelligence-why">
          <div className="section-kicker">
            <Activity size={13} />
            <span>WHY THIS MATTERS</span>
          </div>
          {matterPoints.length > 0 && (
            <ul className="why-list">
              {matterPoints.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          )}
          <p className="why-sentence">
            {band === "High"
              ? "The latest assessment sits in the high band. Review the supporting signal, then decide on a voluntary follow-up."
              : band === "Moderate"
                ? "The latest assessment sits in the moderate band. Monitor the pattern and confirm the next step with the person."
                : "The latest assessment sits in the low band. No immediate action flagged — continue routine monitoring."}
          </p>
        </div>

        <div className="intelligence-next">
          <div className="section-kicker">
            <ShieldCheck size={13} />
            <span>NEXT HUMAN STEP</span>
          </div>
          <p className="next-text">
            Open the personnel profile to review the full assessment, supporting evidence and welfare record before deciding.
            AI supports this review — the human decision remains with the welfare officer.
          </p>
          <Link
            to={`/personnel/${personnel.id}`}
            className={`action-button action-button-${riskTone(band)}`}
            data-testid="open-profile-button"
          >
            <span>Open profile</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        <div className="intelligence-note">
          <ShieldCheck size={12} />
          <span>Decision support only — never a diagnosis or an automated action.</span>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function FocusConnector({ sourceRef, targetRef, activeId }: { sourceRef: RefObject<HTMLDivElement | null>; targetRef: RefObject<HTMLDivElement | null>; activeId: string | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [geometry, setGeometry] = useState<{ line: string; arrow: string; startX: number; startY: number; endX: number; endY: number } | null>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const source = sourceRef.current;
    const target = targetRef.current;
    if (!container || !source || !target) {
      setGeometry(null);
      return;
    }

    const compute = () => {
      const cRect = container.getBoundingClientRect();
      const sRect = source.getBoundingClientRect();
      const tRect = target.getBoundingClientRect();

      const startX = sRect.right - cRect.left;
      const startY = sRect.top + sRect.height / 2 - cRect.top;

      const endX = tRect.left - cRect.left;
      const topY = tRect.top - cRect.top;
      const bottomY = tRect.bottom - cRect.top;
      const endY = Math.max(topY + 48, Math.min(startY, bottomY - 48));

      const cx = (startX + endX) / 2;
      const line = `M ${startX} ${startY} C ${cx} ${startY}, ${cx} ${endY}, ${endX - 8} ${endY}`;
      const arrow = `M ${endX - 8} ${endY - 4} L ${endX} ${endY} L ${endX - 8} ${endY + 4}`;

      setGeometry({ line, arrow, startX, startY, endX, endY });
    };

    compute();
    const resizeObserver = new ResizeObserver(compute);
    resizeObserver.observe(container);
    resizeObserver.observe(source);
    resizeObserver.observe(target);

    window.addEventListener("resize", compute);
    if (typeof document !== "undefined" && document.fonts?.ready) {
      document.fonts.ready.then(() => compute()).catch(() => undefined);
    }

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", compute);
    };
  }, [sourceRef, targetRef, activeId]);

  return (
    <div className={`focus-connector${geometry ? " focus-connector-active" : ""}`} ref={containerRef} aria-hidden="true">
      <svg width="100%" height="100%" fill="none">
        {geometry && (
          <>
            <path className="focus-connector-line" d={geometry.line} />
            <path className="focus-connector-arrow" d={geometry.arrow} />
            <circle className="focus-connector-source" cx={geometry.startX} cy={geometry.startY} r={2.5} />
            <circle className="focus-connector-landing" cx={geometry.endX} cy={geometry.endY} r={2.5} />
          </>
        )}
      </svg>
    </div>
  );
}