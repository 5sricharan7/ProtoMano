import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import type { Variants } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  Check,
  ChevronDown,
  EyeOff,
  Fingerprint,
  HeartHandshake,
  RefreshCw,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type { Overview, UnitOverview, UnitOverviewResponse } from "@/lib/types";

const fetchOverview = () => apiGet<Overview>("/overview");
const fetchUnits = () => apiGet<UnitOverviewResponse>("/overview/units");

type SourceTone = "ready" | "partial" | "error" | "loading";
type SummaryKey = "assessments" | "interventions" | "high-risk";

const pageWrap: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.11, delayChildren: 0.08 } },
};

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.2, 0.7, 0.3, 1] } },
};

const heroWrap: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const heroItem: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.2, 0.7, 0.3, 1] } },
};

export default function CommanderWorkspace() {
  const overviewQuery = useQuery({ queryKey: ["commander-overview"], queryFn: fetchOverview, retry: false });
  const unitsQuery = useQuery({ queryKey: ["commander-units"], queryFn: fetchUnits, retry: false });

  const hadData = overviewQuery.data !== undefined || unitsQuery.data !== undefined;
  const anyError = overviewQuery.isError || unitsQuery.isError;
  const bothReady = overviewQuery.isSuccess && unitsQuery.isSuccess;

  let statusLabel: string;
  let statusTone: SourceTone;
  if (bothReady) {
    statusLabel = "Aggregate intelligence available";
    statusTone = "ready";
  } else if (anyError && hadData) {
    statusLabel = "Aggregate intelligence partially available";
    statusTone = "partial";
  } else if (anyError) {
    statusLabel = "Unable to load aggregate intelligence";
    statusTone = "error";
  } else {
    statusLabel = "Loading aggregate intelligence…";
    statusTone = "loading";
  }

  const isRefreshing = overviewQuery.isFetching || unitsQuery.isFetching;
  function refresh() {
    if (isRefreshing) return;
    void overviewQuery.refetch();
    void unitsQuery.refetch();
  }

  const unitsReady = unitsQuery.isSuccess && (unitsQuery.data?.units.length ?? 0) > 0;

  return (
    <MotionConfig reducedMotion="user">
      <div className="page-frame commander-dashboard" data-testid="commander-dashboard">
        <CommanderAmbient />

        <motion.div className="commander-content" variants={pageWrap} initial="hidden" animate="show">
          <motion.header className="commander-hero" variants={heroWrap}>
            <svg className="commander-hero-motif" viewBox="0 0 240 240" fill="none" aria-hidden="true">
              <circle cx="190" cy="60" r="42" stroke="currentColor" strokeOpacity="0.16" />
              <circle cx="190" cy="60" r="66" stroke="currentColor" strokeOpacity="0.09" />
              <circle cx="190" cy="60" r="92" stroke="currentColor" strokeOpacity="0.05" />
              <circle cx="190" cy="60" r="3.5" fill="currentColor" fillOpacity="0.4" />
              <path d="M 190 18 A 42 42 0 0 1 232 60" stroke="currentColor" strokeOpacity="0.32" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M 190 102 v6 M 184 60 h-6 M 196 60 h6" stroke="currentColor" strokeOpacity="0.22" strokeWidth="1.2" strokeLinecap="round" />
              <path d="M 26 200 h40 M 26 180 h40 M 26 160 h26" stroke="currentColor" strokeOpacity="0.13" strokeWidth="1" strokeLinecap="round" />
              <path d="M 46 180 v22 M 66 200 v18" stroke="currentColor" strokeOpacity="0.13" strokeWidth="1" strokeLinecap="round" />
              <path d="M 8 232 L 232 232" stroke="currentColor" strokeOpacity="0.08" strokeWidth="1" />
              <circle cx="46" cy="120" r="10" stroke="currentColor" strokeOpacity="0.1" />
              <circle cx="46" cy="120" r="16" stroke="currentColor" strokeOpacity="0.07" />
              <circle cx="46" cy="120" r="1.5" fill="currentColor" fillOpacity="0.3" />
            </svg>

            <motion.div className="commander-hero-copy" variants={heroItem}>
              <span className="command-eyebrow">
                <span className="command-eyebrow-dot" />
                COMMAND 02
                <span className="commander-eyebrow-sep">/</span>
                <strong>WELFARE COMMAND</strong>
              </span>
              <h1>Unit welfare <em>intelligence</em></h1>
              <p className="commander-hero-lede">
                Protected aggregate signals for understanding welfare conditions across your unit — awareness, not judgment.
              </p>
              <span className="demo-data-indicator">
                <span className="demo-pip" /> DEMO DATA <span className="demo-pip-sep">|</span> Synthetic records
              </span>
            </motion.div>

            <motion.div className="commander-hero-side" variants={heroItem}>
              <div className={`commander-status source-${statusTone}`} role="status" aria-live="polite" data-testid="commander-source-status">
                <span className="commander-status-icon"><ShieldCheck size={15} /></span>
                <span className="commander-status-meta">
                  <strong>Protected aggregate</strong>
                  <span className="commander-status-state"><i /> {statusLabel}</span>
                </span>
              </div>
              <button type="button" className="commander-refresh" onClick={refresh} disabled={isRefreshing} data-testid="commander-refresh" aria-label="Refresh aggregate intelligence">
                <RefreshCw size={13} className={isRefreshing ? "commander-refresh-spin" : undefined} />
                {isRefreshing ? "Refreshing…" : "Refresh"}
              </button>
            </motion.div>
          </motion.header>

          <motion.div variants={fadeUp}>
            <CurrentPicture query={overviewQuery} onRetry={() => void overviewQuery.refetch()} />
          </motion.div>

          <InfoConnector active={unitsReady} />

          <motion.div variants={fadeUp}>
            <UnitLandscape query={unitsQuery} overview={overviewQuery.data} onRetry={() => void unitsQuery.refetch()} />
          </motion.div>
        </motion.div>

        <motion.div
          className="commander-lower"
          variants={fadeUp}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.12 }}
        >
          <SignalsBlock overview={overviewQuery.data} units={unitsQuery.data} />
          <PrivacyFeature />
        </motion.div>

        <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.4 }}>
          <HitlNote />
        </motion.div>
      </div>
    </MotionConfig>
  );
}

function CommanderAmbient() {
  return (
    <motion.div
      className="commander-ambient"
      aria-hidden="true"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.9, ease: "easeOut" }}
    />
  );
}

function InfoConnector({ active }: { active: boolean }) {
  return (
    <div className={`info-connector${active ? " is-active" : ""}`} aria-hidden="true">
      <span className="info-connector-node" />
      <span className="info-connector-line" />
      <svg className="info-connector-arrow" width="10" height="12" viewBox="0 0 10 12" fill="none">
        <path d="M5 2 v7 M2 7 l3 3 3 -3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function AnimatedValue({ value }: { value: number | string }) {
  const key = String(value);
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={key}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.22, ease: [0.2, 0.7, 0.3, 1] }}
      >
        {value}
      </motion.span>
    </AnimatePresence>
  );
}

function CurrentPicture({ query, onRetry }: { query: UseQueryResult<Overview, Error>; onRetry: () => void }) {
  const [activeSummary, setActiveSummary] = useState<SummaryKey | null>(null);

  const loading = query.isLoading || (query.isPending && query.data === undefined);

  if (loading) {
    return (
      <section className="commander-metrics-band" data-testid="commander-metrics-loading" aria-label="Loading aggregate metrics">
        <header className="stage-head stage-head--mint" aria-hidden="true">
          <span className="stage-num">01</span>
          <span className="stage-head-eyebrow">Observe</span>
        </header>
        <div className="current-picture-grid">
          <div className="commander-skeleton metric-cell-skeleton" />
          <div className="commander-skeleton metric-cell-skeleton" />
        </div>
      </section>
    );
  }

  if (query.isError) {
    return (
      <div className="commander-metric-error" data-testid="commander-metrics-error" role="alert">
        <AlertTriangle size={16} />
        <span>Unable to load aggregate metrics.</span>
        <button type="button" onClick={onRetry} data-testid="commander-metrics-retry">Retry</button>
      </div>
    );
  }

  const overview = query.data as Overview | undefined;

  const summaryItems: { key: SummaryKey; label: string; value: number | null; icon: ReactNode; signal?: boolean; testid: string }[] = [
    { key: "assessments", label: "Assessments today", value: overview?.assessments_today ?? null, icon: <BrainCircuit size={15} />, testid: "metric-assessments" },
    { key: "interventions", label: "Open interventions", value: overview?.open_interventions ?? null, icon: <ShieldCheck size={15} />, testid: "metric-interventions" },
    { key: "high-risk", label: "High-risk latest", value: overview?.high_risk_latest ?? null, icon: <AlertTriangle size={15} />, signal: true, testid: "metric-high-risk" },
  ];

  const activeExplanation: Record<SummaryKey, string> = {
    assessments: "Assessments completed today across the protected cohort.",
    interventions: "Open support actions currently active in the cohort.",
    "high-risk": "Latest count in the high-risk band from the most recent aggregate assessment.",
  };

  return (
    <section className="commander-metrics-band" data-testid="commander-metrics" aria-label="Aggregate overview">
      <header className="stage-head stage-head--mint">
        <span className="stage-num" aria-hidden="true">01</span>
        <div className="stage-head-copy">
          <span className="stage-head-eyebrow">Observe</span>
          <h2>Current picture</h2>
          <p>Today's protected aggregate position across the cohort.</p>
        </div>
      </header>

      <div className="current-picture-grid">
        <div className="primary-metric" data-testid="metric-personnel">
          <div className="primary-metric-icon"><Users size={18} /></div>
          <div className="primary-metric-body">
            <span className="primary-metric-label">Personnel covered</span>
            <strong className="primary-metric-value"><AnimatedValue value={overview?.personnel_count ?? "—"} /></strong>
            <span className="primary-metric-note">personnel in cohort · protected aggregate</span>
          </div>
        </div>

        <div className="summary-rail">
          <div className="cluster-head"><span>Operational indicators</span><span className="cluster-head-time">latest</span></div>
          <div className="summary-grid">
            {summaryItems.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`summary-item${item.signal ? " summary-item--signal" : ""}`}
                data-testid={item.testid}
                aria-pressed={activeSummary === item.key}
                onClick={() => setActiveSummary(activeSummary === item.key ? null : item.key)}
              >
                <span className="summary-item-icon">{item.icon}</span>
                <span className="summary-item-body">
                  <strong><AnimatedValue value={item.value ?? "—"} /></strong>
                  <span>{item.label}</span>
                </span>
              </button>
            ))}
          </div>
          <AnimatePresence>
            {activeSummary !== null && (
              <motion.p
                key={activeSummary}
                className="summary-explain"
                role="status"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2, ease: [0.2, 0.7, 0.3, 1] }}
              >
                <span className="summary-explain-dot" aria-hidden="true" />
                {activeExplanation[activeSummary]}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

function maxPersonnel(units: UnitOverview[]): number {
  const values = units.filter((u) => !u.suppressed).map((u) => u.personnel_count ?? 0);
  return values.length ? Math.max(1, ...values) : 1;
}

function UnitObject({ unit, index, maxValue, minGroupSize, selected, onToggle }: { unit: UnitOverview; index: number; maxValue: number; minGroupSize: number; selected: boolean; onToggle: () => void }) {
  const pct = unit.suppressed ? 0 : Math.max(8, Math.round(((unit.personnel_count ?? 0) / maxValue) * 100));
  return (
    <button
      type="button"
      className={`unit-object${unit.suppressed ? " unit-object--protected" : ""}${selected ? " unit-object--selected" : ""}`}
      onClick={onToggle}
      aria-pressed={selected}
      data-testid={`commander-unit-${index}`}
    >
      <span className="unit-object-focus" aria-hidden="true" />
      <span className="unit-object-head">
        <span className="unit-object-name">{unit.unit}</span>
        {unit.suppressed ? (
          <span className="unit-tile-badge badge--protected"><ShieldCheck size={11} /> Protected</span>
        ) : (
          <span className="unit-tile-badge"><Users size={11} /> Cohort {unit.personnel_count}</span>
        )}
      </span>

      <span className="unit-object-divider" aria-hidden="true" />

      {unit.suppressed ? (
        <span className="unit-object-protected">
          <span className="unit-object-stat"><span>Aggregate signal</span><strong>Withheld</strong></span>
          <span className="unit-object-stat"><span>Cohort size</span><strong>Protected</strong></span>
          <span className="unit-object-msg"><EyeOff size={12} /> Insufficient group size for display. Min. cohort requirement: {minGroupSize}.</span>
        </span>
      ) : (
        <span className="unit-object-metrics">
          <span className="unit-object-stat"><span>Cohort size</span><strong>{unit.personnel_count}</strong></span>
          <span className="unit-object-bar"><span className="unit-object-bar-fill" style={{ width: `${pct}%` }} aria-hidden="true" /></span>
          <span className="unit-object-stat unit-object-stat--signal"><span>Aggregate signal</span><strong>{unit.high_risk_latest ?? 0} high-risk</strong></span>
        </span>
      )}

      <span className="unit-object-foot">
        <span className="unit-object-type">
          {unit.suppressed ? <EyeOff size={11} /> : <Users size={11} />}
          {unit.suppressed ? "Protected aggregate" : "Aggregate visible"}
        </span>
        <span className="unit-object-more">
          {selected ? "Viewing detail" : "View detail"}
          <ArrowRight size={11} />
        </span>
      </span>
    </button>
  );
}

function ProtectedDetail({ overview, minGroupSize, suppressedUnits }: { overview: Overview | undefined; minGroupSize: number; suppressedUnits: number }) {
  const [whyOpen, setWhyOpen] = useState(false);

  return (
    <div className="unit-detail-body unit-detail-body--protected">
      <div className="unit-detail-lock">
        <span className="unit-detail-lock-icon"><EyeOff size={14} /></span>
        <span className="unit-detail-lock-copy">
          <strong>Intentionally protected</strong>
          <span>Aggregate cells withheld — below the minimum cohort requirement.</span>
        </span>
      </div>

      <p className="unit-detail-explanation">
        Information withheld because the available cohort does not meet the minimum group-size requirement for privacy-safe display.
      </p>

      <div className="unit-detail-stats">
        <div className="unit-detail-stat">
          <span>Total in cohort</span>
          <strong>{overview?.personnel_count ?? "—"}</strong>
        </div>
        <div className="unit-detail-stat">
          <span>Minimum required</span>
          <strong>{minGroupSize}</strong>
        </div>
        <div className="unit-detail-stat unit-detail-stat--signal">
          <span>Units withheld</span>
          <strong>{suppressedUnits}</strong>
        </div>
      </div>

      <div className="unit-why">
        <button type="button" className="unit-why-toggle" aria-expanded={whyOpen} onClick={() => setWhyOpen((v) => !v)} data-testid="unit-why-protected">
          <ChevronDown size={13} />
          Why is this protected?
        </button>
        <AnimatePresence initial={false}>
          {whyOpen && (
            <motion.div
              className="unit-why-body"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.24, ease: [0.2, 0.7, 0.3, 1] }}
            >
              <p>
                Individual identifiers and per-person welfare signals never surface in commander views. An aggregate is withheld whenever the group it describes is too small — here, below {minGroupSize} personnel — because small counts can effectively be used to infer individual outcomes. Aggregates across the whole cohort remain available to you.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function VisibleDetail({ unit, maxValue }: { unit: UnitOverview; maxValue: number }) {
  const pct = Math.max(8, Math.round(((unit.personnel_count ?? 0) / maxValue) * 100));
  return (
    <div className="unit-detail-body unit-detail-body--visible">
      <div className="unit-detail-stats unit-detail-stats--pair">
        <div className="unit-detail-stat">
          <span>Cohort size</span>
          <strong>{unit.personnel_count}</strong>
        </div>
        <div className="unit-detail-stat unit-detail-stat--signal">
          <span>Aggregate signal</span>
          <strong>{unit.high_risk_latest ?? 0} high-risk</strong>
        </div>
      </div>
      <div className="unit-detail-bar"><span className="unit-detail-bar-fill" style={{ width: `${pct}%` }} aria-hidden="true" /></div>
      <p className="unit-detail-explanation">
        Visible aggregate summary for this unit's protected cohort. No individual information is shown.
      </p>
    </div>
  );
}

function UnitLandscape({ query, overview, onRetry }: { query: UseQueryResult<UnitOverviewResponse, Error>; overview: Overview | undefined; onRetry: () => void }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const data = query.data;

  useEffect(() => {
    if (data && data.units.length > 0 && selectedId === null) {
      setSelectedId(data.units[0].unit);
    }
  }, [data, selectedId]);

  const selected = data?.units.find((u) => u.unit === selectedId) ?? null;
  const suppressedCount = data?.suppressed_units ?? 0;

  return (
    <section className="unit-intelligence" data-testid="commander-units" aria-labelledby="units-heading">
      <header className="stage-head stage-head--cyan">
        <span className="stage-num" aria-hidden="true">02</span>
        <div className="stage-head-copy">
          <span className="stage-head-eyebrow">Focus</span>
          <h2 id="units-heading">Unit landscape</h2>
          <p>Select a unit to focus its protected aggregate signal.</p>
        </div>
        {data && data.min_group_size > 0 && (
          <span className="stage-head-note">MINIMUM COHORT REQUIREMENT {data.min_group_size}</span>
        )}
      </header>

      {query.isLoading && (
        <div className="unit-landscape" data-testid="commander-units-loading" aria-label="Loading unit aggregates">
          {[0, 1, 2].map((i) => <div key={i} className="commander-skeleton unit-tile-skeleton" />)}
        </div>
      )}

      {query.isError && (
        <div className="commander-panel-error" role="alert" data-testid="commander-units-error">
          <AlertTriangle size={16} />
          <span>Unable to load unit aggregates.</span>
          <button type="button" onClick={onRetry} data-testid="commander-units-retry">Retry</button>
        </div>
      )}

      {query.isSuccess && data && data.units.length === 0 && (
        <div className="commander-panel-empty" data-testid="commander-units-empty">
          <Fingerprint size={18} />
          <span>Unit aggregate data is not available yet.</span>
        </div>
      )}

      {query.isSuccess && data && data.units.length > 0 && (
        <>
          <p className="unit-selection-status" role="status" aria-live="polite">
            Viewing · <strong>{selected ? selected.unit : "No unit selected"}</strong>
          </p>
          <ul className="unit-landscape" data-testid="commander-unit-list" data-focus={selected ? "true" : "false"}>
            {data.units.map((unit, index) => (
              <li key={`${unit.unit}-${index}`}>
                <UnitObject
                  unit={unit}
                  index={index}
                  maxValue={maxPersonnel(data.units)}
                  minGroupSize={data.min_group_size}
                  selected={unit.unit === selectedId}
                  onToggle={() => setSelectedId(unit.unit === selectedId ? null : unit.unit)}
                />
              </li>
            ))}
          </ul>

          <AnimatePresence mode="wait">
            {selected && (
              <motion.div
                key={selected.unit}
                className="unit-detail"
                data-testid="commander-unit-detail"
                initial={{ opacity: 0, y: 12, scale: 0.982 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.988 }}
                transition={{ duration: 0.3, ease: [0.2, 0.7, 0.3, 1] }}
              >
                <motion.span
                  className="unit-detail-beam"
                  aria-hidden="true"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.12, ease: "easeOut" }}
                />
                <div className="unit-detail-head">
                  <div className="unit-detail-heading">
                    <span className="unit-detail-kicker">Explore · Contextual detail</span>
                    <h3 className="unit-detail-title">{selected.unit}</h3>
                  </div>
                  <button type="button" className="unit-detail-close" onClick={() => setSelectedId(null)} data-testid="unit-detail-close">
                    Close
                  </button>
                </div>

                {selected.suppressed ? (
                  <ProtectedDetail overview={overview} minGroupSize={data.min_group_size} suppressedUnits={data.suppressed_units} />
                ) : (
                  <VisibleDetail unit={selected} maxValue={maxPersonnel(data.units)} />
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {suppressedCount > 0 && (
            <p className="privacy-legend">
              Aggregate cells withheld for {suppressedCount} {suppressedCount === 1 ? "unit" : "units"} below the minimum cohort requirement.
            </p>
          )}
        </>
      )}
    </section>
  );
}

function SignalsBlock({ overview, units }: { overview: Overview | undefined; units: UnitOverviewResponse | undefined }) {
  const highRisk = overview?.high_risk_latest ?? units?.high_risk_latest_total ?? null;
  const personnelTotal = overview?.personnel_count ?? units?.total_personnel_count ?? null;
  const suppressedUnits = units?.suppressed_units ?? null;
  const minGroupSize = units?.min_group_size ?? null;
  const loading = overview === undefined && units === undefined;

  return (
    <section className="commander-signals" data-testid="commander-signals" aria-labelledby="signals-heading">
      <header className="stage-head stage-head--amber">
        <span className="stage-num" aria-hidden="true">03</span>
        <div className="stage-head-copy">
          <span className="stage-head-eyebrow">Understand</span>
          <h2 id="signals-heading">Signals requiring attention</h2>
          <p>Aggregate signals describe cohorts, not individuals — awareness, not judgment.</p>
        </div>
      </header>

      <div className="signals-card">
        <div className="signals-card-main">
          <span className="signals-icon"><AlertTriangle size={18} /></span>
          <div className="signals-card-copy">
            <strong>{loading ? "Loading aggregates…" : "High-risk assessments detected"}</strong>
            <span>Latest available assessments in the protected cohort.</span>
          </div>
        </div>
        <div className="signals-value-row">
          <span className="signals-value-label">LATEST COHORT</span>
          <strong className="signals-value">{highRisk === null ? "—" : highRisk}</strong>
        </div>
      </div>

      <div className="signals-notes">
        {loading && <span>Aggregate signals will appear when protected data is available.</span>}
        {personnelTotal !== null && <span>Protected cohort: <strong>{personnelTotal} personnel</strong>.</span>}
        {suppressedUnits !== null && suppressedUnits > 0 && minGroupSize !== null && (
          <span>Signal withheld for {suppressedUnits} {suppressedUnits === 1 ? "unit" : "units"} below the minimum cohort requirement.</span>
        )}
        <span className="signals-caveat">This system supports welfare awareness — it does not diagnose personnel.</span>
      </div>
    </section>
  );
}

function PrivacyFeature() {
  const allowed = ["Aggregate unit signals", "Protected cohort counts", "Authorized operational summaries"];
  const denied = ["Personnel identity", "Individual risk", "Individual welfare records", "Individual interventions", "Individual biometrics"];
  return (
    <aside className="privacy-feature" data-testid="commander-privacy" aria-labelledby="privacy-heading">
      <header className="stage-head stage-head--gold">
        <span className="stage-num" aria-hidden="true">04</span>
        <div className="stage-head-copy">
          <span className="stage-head-eyebrow">Respond</span>
          <h2 id="privacy-heading">Architectural privacy</h2>
          <p>Commander access is intentionally aggregate. Individual welfare records never enter this workspace.</p>
        </div>
      </header>
      <div className="privacy-split">
        <div className="privacy-box privacy-box--allowed">
          <h3>COMMANDER VISIBILITY</h3>
          <ul>
            {allowed.map((a) => <li key={a}><Check size={13} /> {a}</li>)}
          </ul>
        </div>
        <div className="privacy-box privacy-box--denied">
          <h3>INDIVIDUAL INFORMATION</h3>
          <ul>
            {denied.map((a) => <li key={a}><X size={13} /> {a}</li>)}
          </ul>
        </div>
      </div>
    </aside>
  );
}

function HitlNote() {
  return (
    <footer className="commander-hitl" data-testid="commander-hitl">
      <HeartHandshake size={15} />
      <span className="commander-hitl-tag">Human-in-the-loop</span>
      <span className="commander-hitl-text">Aggregate intelligence supports command awareness. Welfare decisions remain with authorized human personnel.</span>
    </footer>
  );
}