import Link from "next/link";
import { ArrowRight, Drop, FileText, MapPin, SquaresFour } from "@phosphor-icons/react/dist/ssr";
import { getIncidents, parseApiDate } from "@/services/incidents";
import type { IncidentListItem } from "@/types/incident";

export const dynamic = "force-dynamic";

function formatDate(value: string) {
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "Asia/Ho_Chi_Minh" }).format(date);
}

export default async function CasesPage() {
  let incidents: IncidentListItem[] = [];
  let error = "";
  try { incidents = await getIncidents(); }
  catch (caught) { error = caught instanceof Error ? caught.message : "The incident service is unavailable."; }
  const pending = incidents.reduce((sum, item) => sum + item.pending_decision_count, 0);
  const evidence = incidents.reduce((sum, item) => sum + item.evidence_count, 0);

  return <div className="app-shell">
    <a className="skip-link" href="#case-list">Skip to cases</a>
    <aside className="sidebar" aria-label="Primary navigation">
      <Link className="brand" href="/cases"><span className="logo-mark"><Drop size={19} weight="fill" aria-hidden="true" /></span><span className="brand-name"><span>Aqua</span><span>Pass</span></span></Link>
      <p className="nav-caption">WORKSPACE</p>
      <nav className="primary-nav" aria-label="Workspace navigation"><Link className="nav-item nav-item-active" href="/cases" aria-current="page"><SquaresFour size={19} weight="regular" aria-hidden="true" /><span>Cases</span></Link></nav>
      <div className="sidebar-bottom"><span>WORKSPACE</span><strong>Incident operations</strong></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div className="breadcrumb"><span>Operations</span><span aria-hidden="true">/</span><strong>Cases</strong></div><span className="topbar-meta">AquaPass <span aria-hidden="true">/</span> Operations</span></header>
      <div className="workspace index-workspace" id="case-list">
        <div className="case-heading index-heading"><div><p className="eyebrow">INCIDENT MANAGEMENT</p><h1>Cases</h1><p>Open a case to review its decision, evidence and workflow.</p></div></div>
        <div className="index-stats"><div><span>OPEN CASES</span><strong>{incidents.length}</strong></div><div><span>PENDING DECISIONS</span><strong>{pending}</strong></div><div><span>EVIDENCE RECORDS</span><strong>{evidence}</strong></div></div>
        <section className="panel case-register" aria-labelledby="register-title"><div className="section-heading"><div><p className="eyebrow">CASE REGISTER</p><h2 id="register-title">All incidents</h2></div><span className="count-label">{incidents.length} total</span></div>
          {error && <p className="inline-alert" role="alert">Cannot load cases: {error}</p>}
          {!error && !incidents.length && <p className="empty-state">No incidents recorded. Create an incident through the API to see it here.</p>}
          <ul className="case-list">{incidents.map((item) => <li key={item.id}><Link href={`/incidents/${item.id}`} className="case-row"><span className="case-icon"><FileText size={20} weight="regular" aria-hidden="true" /></span><span className="case-copy"><strong>{item.title}</strong><small><MapPin size={14} aria-hidden="true" /> {item.location_name} · Updated {formatDate(item.updated_at)}</small></span><span className={`status status-${item.status.toLowerCase().replaceAll("_", "-")}`}>{item.status.replaceAll("_", " ")}</span><span className="case-stat"><strong>{item.pending_decision_count}</strong><small>pending</small></span><span className="case-stat"><strong>{item.evidence_count}</strong><small>evidence</small></span><ArrowRight size={19} aria-hidden="true" /></Link></li>)}</ul>
        </section>
      </div>
    </main>
  </div>;
}
