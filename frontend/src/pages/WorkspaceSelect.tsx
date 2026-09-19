import { Link } from "react-router-dom";
import { ArrowRight, Command, Fingerprint, HeartHandshake, ShieldCheck, UserRound } from "lucide-react";
import { HERO_BACKGROUND_URL } from "@/lib/config";

export default function WorkspaceSelect() {
  return (
    <div className="reference-login">
      <header className="demo-header">
        <Link to="/" className="reference-brand" data-testid="login-brand-link">
          <span className="reference-brand-mark">
            <Fingerprint size={24} />
          </span>
          <span>
            <strong>Manobal<span>-AI</span></strong>
            <small>Welfare Signal</small>
          </span>
        </Link>
        <nav>
          <Link to="/">Home</Link>
          <Link to="/#how-it-works">How it works</Link>
          <Link to="/#ethics">Privacy & ethics</Link>
        </nav>
      </header>
      <div className="demo-layout">
        <section
          className="demo-story"
          style={{
            backgroundImage: `linear-gradient(105deg, rgba(246,243,234,.96) 0%, rgba(255,253,248,.90) 40%, rgba(255,253,248,.62) 72%, rgba(255,253,248,.45) 100%), url(${HERO_BACKGROUND_URL})`,
          }}
        >
          <div>
            <span className="demo-story-kicker">MANOBAL-AI</span>
            <h1>Personnel Welfare<br /><em>Intelligence.</em></h1>
            <i className="demo-story-rule" />
            <p>
              Every welfare signal deserves care. Choose the operational workspace that
              matches how you serve — every path stays protected and human-in-the-loop.
            </p>
          </div>
          <footer>
            <span>
              <ShieldCheck size={20} /> HUMAN-IN-THE-LOOP • WELFARE-ONLY PURPOSE
            </span>
            <strong>People. Prepared. Protected.</strong>
          </footer>
        </section>
        <main className="demo-command">
          <div className="demo-command-inner">
            <span className="demo-command-kicker">OPERATIONAL ACCESS</span>
            <h2>Choose your<br /><em>operational workspace.</em></h2>
            <p>
              Select the workspace aligned to your role. Authentication and access are
              verified against your account credentials.
            </p>

            <div className="workspace-grid">
              <Link to="/login/officer" className="workspace-card" data-testid="workspace-officer-card">
                <div className="workspace-card-head">
                  <span className="workspace-card-icon"><HeartHandshake size={22} /></span>
                  <h3>Welfare Officer</h3>
                </div>
                <p>Review personnel welfare signals, understand risk factors, and coordinate support.</p>
                <span className="workspace-card-cta">Continue as Welfare Officer <ArrowRight size={14} /></span>
              </Link>

              <Link to="/login/commander" className="workspace-card workspace-card--commander" data-testid="workspace-commander-card">
                <div className="workspace-card-head">
                  <span className="workspace-card-icon"><Command size={22} /></span>
                  <h3>Commander</h3>
                </div>
                <p>View protected unit-level welfare intelligence and aggregate readiness signals.</p>
                <span className="workspace-card-cta">Continue as Commander <ArrowRight size={14} /></span>
              </Link>
            </div>

            <Link to="/login/personnel" className="workspace-personnel" data-testid="workspace-personnel-card">
              <UserRound size={15} /> Personnel teammate workspace <ArrowRight size={13} />
            </Link>

            <div className="demo-notice">
              <ShieldCheck size={19} />
              <span>
                Workspace selection is presentation only — every path is authenticated against
                the real backend and matched to your account role.
              </span>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}