import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, BrainCircuit, Database, HeartHandshake, ShieldCheck, CheckCircle2, Activity, Cpu } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { useLayoutEffect, useRef, useState, type Ref, type RefObject } from "react";

// Interactive 6-stage welfare intelligence flow
const stages = [
  { id: 1, number: "01", label: "INPUT DATA", title: "Personnel & welfare data", description: "Recent duty, rest, leave, self-reported wellbeing and available supporting signals.", why: "Provides the evidence base for the assessment.", icon: Database, accent: "accent-teal" },
  { id: 2, number: "02", label: "DATA PREPARATION", title: "Validated runtime data", description: "Recent observations are validated and prepared using the deployed preprocessing pipeline.", why: "Helps ensure the assessment uses usable observations.", icon: Cpu, accent: "accent-blue" },
  { id: 3, number: "03", label: "AI ASSESSMENT", title: "Calibrated risk engine", description: "The deployed model evaluates the available evidence and produces a risk probability distribution.", why: "Converts evidence into a structured risk signal.", icon: BrainCircuit, accent: "accent-purple" },
  { id: 4, number: "04", label: "RISK RESULT", title: "Risk assessment", description: "The available evidence is translated into a Low, Moderate or High risk assessment.", why: "Produces interpretable risk bands for welfare review.", icon: Activity, accent: "accent-amber" },
  { id: 5, number: "05", label: "EVIDENCE & TRUST", title: "Evidence quality", description: "Data completeness, recency, validity and consistency are considered separately from model confidence.", why: "Separates evidence reliability from model confidence scores.", icon: CheckCircle2, accent: "accent-cyan" },
  { id: 6, number: "06", label: "OFFICER REVIEW", title: "Human welfare decision", description: "The assessment supports review. The Welfare Officer remains responsible for the final welfare decision.", why: "Human judgment remains central to welfare decisions.", icon: HeartHandshake, accent: "accent-green" },
];

export default function Analysis() {
  const [selectedStage, setSelectedStage] = useState(1);
  const currentStage = stages.find(s => s.id === selectedStage) || stages[0];
  const stage03NodeRef = useRef<HTMLButtonElement>(null);
  const stage04NodeRef = useRef<HTMLButtonElement>(null);

  return (
    <div className="page-frame analysis-page" data-testid="analysis-screen">
      <div className="pipeline-page-header">
        <div className="pipeline-title-wrap">
          <span className="pipeline-eyebrow">
            <span className="pipeline-eyebrow-kicker">AI analysis</span>
            <span className="pipeline-eyebrow-sep" />
            <span>Welfare Intelligence Flow</span>
          </span>
          <h1>From personnel and welfare data to trusted, <em>explainable assessment.</em></h1>
          <p className="pipeline-subtitle">An interactive map of the welfare assessment process — six compact stages from data to human review.</p>
        </div>
        <div className="pipeline-status">
          <ShieldCheck size={13} />
          <span>Confidential • Welfare use only</span>
        </div>
      </div>

      <div className="pipeline-interactive-flow">
        {/* Interactive connected flow */}
        <div className="flow-diagram" role="group" aria-label="Welfare intelligence flow stages">
          <div className="flow-row">
            <FlowNode stage={stages[0]} isSelected={selectedStage === 1} onSelect={setSelectedStage} />
            <FlowConnector direction="horizontal" isActive={selectedStage === 1 || selectedStage === 2} />
            <FlowNode stage={stages[1]} isSelected={selectedStage === 2} onSelect={setSelectedStage} />
            <FlowConnector direction="horizontal" isActive={selectedStage === 2 || selectedStage === 3} />
            <FlowNode stage={stages[2]} nodeRef={stage03NodeRef} isSelected={selectedStage === 3} onSelect={setSelectedStage} />
          </div>

          <SnakeConnector
            sourceRef={stage03NodeRef}
            targetRef={stage04NodeRef}
            isActive={selectedStage === 3 || selectedStage === 4}
          />

          <div className="flow-row">
            <FlowNode stage={stages[3]} nodeRef={stage04NodeRef} isSelected={selectedStage === 4} onSelect={setSelectedStage} />
            <FlowConnector direction="horizontal" isActive={selectedStage === 4 || selectedStage === 5} />
            <FlowNode stage={stages[4]} isSelected={selectedStage === 5} onSelect={setSelectedStage} />
            <FlowConnector direction="horizontal" isActive={selectedStage === 5 || selectedStage === 6} />
            <FlowNode stage={stages[5]} isSelected={selectedStage === 6} onSelect={setSelectedStage} />
          </div>

          <div className="flow-path">
            <span className="flow-path-label">Assessment path</span>
            <div className="flow-path-steps">
              <span>Data</span>
              <ArrowRight size={12} className="flow-path-arrow" />
              <span>Evidence</span>
              <ArrowRight size={12} className="flow-path-arrow" />
              <span>Risk</span>
              <ArrowRight size={12} className="flow-path-arrow" />
              <span>Explanation</span>
              <ArrowRight size={12} className="flow-path-arrow" />
              <span>Human review</span>
            </div>
          </div>
        </div>

        {/* Detail panel */}
        <div className={`detail-panel ${currentStage.accent}`}>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={currentStage.id}
              className="detail-panel-content"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
            >
              <div className="detail-header">
                <span className="detail-step">{currentStage.number}</span>
                <span className="detail-label">{currentStage.label}</span>
              </div>
              <h3 className="detail-title">{currentStage.title}</h3>
              <p className="detail-description">{currentStage.description}</p>
              <div className="detail-why">
                <span className="why-label">Why this matters</span>
                <p className="why-text">{currentStage.why}</p>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <Card className="pipeline-human-note">
        <div className="human-note-icon"><HeartHandshake size={20} /></div>
        <div className="human-note-text">
          <h4>AI assists. Officers decide.</h4>
          <p>The platform identifies changes in signal. A welfare officer brings context, consent and care to what happens next.</p>
        </div>
        <Link to="/interventions" className="primary-cta compact-cta" data-testid="analysis-open-interventions-link">
          Open intervention desk <ArrowRight size={15} />
        </Link>
      </Card>

      <div className="pipeline-nav">
        <Link to="/officer" className="text-link" data-testid="analysis-back-command-link">Back to command</Link>
      </div>
    </div>
  );
}

function FlowNode({ stage, isSelected, onSelect, nodeRef }: { stage: typeof stages[0]; isSelected: boolean; onSelect: (id: number) => void; nodeRef?: Ref<HTMLButtonElement> }) {
  const Icon = stage.icon;

  return (
    <motion.button
      ref={nodeRef}
      className={`flow-node ${stage.accent} ${isSelected ? "flow-node-selected" : ""}`}
      onClick={() => onSelect(stage.id)}
      type="button"
      aria-pressed={isSelected}
      aria-label={`Stage ${stage.number}: ${stage.label}`}
      whileHover={{ scale: 1.04 }}
      whileTap={{ scale: 0.97 }}
    >
      <div className="flow-node-content">
        <div className="flow-node-number">{stage.number}</div>
        <div className="flow-node-icon">
          <Icon size={16} />
        </div>
      </div>
      <span className="flow-node-label">{stage.label}</span>
    </motion.button>
  );
}

function FlowConnector({ direction, isActive }: { direction: "horizontal" | "vertical"; isActive?: boolean }) {
  const className = [
    direction === "horizontal" ? "flow-connector" : "flow-connector-vertical",
    isActive ? "flow-connector-active" : "",
  ].filter(Boolean).join(" ");

  return (
    <div className={className} aria-hidden="true">
      <span className="flow-connector-line" />
      <svg className="flow-connector-arrow" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
        {direction === "horizontal"
          ? <path d="M1 1.5 L8 6 L1 10.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          : <path d="M1.5 1 L6 8 L10.5 1" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />}
      </svg>
    </div>
  );
}

function SnakeConnector({ sourceRef, targetRef, isActive }: { sourceRef: RefObject<HTMLButtonElement | null>; targetRef: RefObject<HTMLButtonElement | null>; isActive?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [geometry, setGeometry] = useState<{ line: string; arrow: string } | null>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const source = sourceRef.current;
    const target = targetRef.current;
    if (!container || !source || !target) return;

    const compute = () => {
      const cRect = container.getBoundingClientRect();
      const sRect = source.getBoundingClientRect();
      const tRect = target.getBoundingClientRect();

      const sx = sRect.left - cRect.left + sRect.width / 2;
      const syB = sRect.bottom - cRect.top;
      const tx = tRect.left - cRect.left + tRect.width / 2;
      const tyT = tRect.top - cRect.top;

      const arrowLen = 9;
      const midY = syB + (tyT - syB) / 2;

      setGeometry({
        line: `M ${sx} ${syB} L ${sx} ${midY} L ${tx} ${midY} L ${tx} ${tyT - arrowLen}`,
        arrow: `M ${tx - 5} ${tyT - arrowLen} L ${tx} ${tyT} L ${tx + 5} ${tyT - arrowLen}`,
      });
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
  }, [sourceRef, targetRef]);

  const className = ["flow-snake-connector", isActive ? "flow-snake-active" : ""].filter(Boolean).join(" ");

  return (
    <div className={className} ref={containerRef} aria-hidden="true">
      <svg width="100%" height="100%" fill="none" aria-hidden="true">
        {geometry && (
          <>
            <path className="flow-snake-line" d={geometry.line} />
            <path className="flow-snake-arrow" d={geometry.arrow} />
          </>
        )}
      </svg>
    </div>
  );
}