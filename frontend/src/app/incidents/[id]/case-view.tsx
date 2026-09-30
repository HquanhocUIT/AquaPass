import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowRight,
  ChartBar,
  ClipboardText,
  ClockCounterClockwise,
  Drop,
  FileText,
  Graph,
  Info,
  MapPin,
  Scales,
  SquaresFour,
} from "@phosphor-icons/react/dist/ssr";
import { getIncidentWorkspace, IncidentNotFoundError, parseApiDate } from "@/services/incidents";
import type { Evidence } from "@/types/incident";
import { WorkflowActions } from "./workflow-actions";

export type CaseSection = "decision" | "evidence" | "map" | "ranking" | "workflow" | "activity";

type GraphEdge = {
  graph_id: string;
  source_node: string;
  relationship: string;
  target_node: string;
  state: string;
  rationale: string;
};

const sectionNames: Record<CaseSection, string> = {
  decision: "Decision",
  evidence: "Evidence",
  map: "Evidence map",
  ranking: "Ranking",
  workflow: "Workflow",
  activity: "Activity",
};

const sectionIcons = { decision: Scales, evidence: FileText, map: Graph, ranking: ChartBar, workflow: ClipboardText, activity: ClockCounterClockwise };

function formatDate(value: string) {
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Ho_Chi_Minh" }).format(date);
}

function valueOf(item: Evidence) {
  return item.value_numeric !== null ? `${item.value_numeric} ${item.unit ?? ""}`.trim() : item.value_text || "No value recorded";
}

function pagePath(id: string, section: CaseSection) {
  return `/incidents/${id}${section === "decision" ? "" : `/${section}`}`;
}

function SectionHeading({ eyebrow, title, note, side }: { eyebrow: string; title: string; note?: string; side?: React.ReactNode }) {
  return <div className="section-heading"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2>{note && <p>{note}</p>}</div>{side}</div>;
}

export async function CaseView({ id, section }: { id: string; section: CaseSection }) {
  let workspace;
  try { workspace = await getIncidentWorkspace(id); }
  catch (error) { if (error instanceof IncidentNotFoundError) notFound(); throw error; }
  const { incident, decisionDetail, intelligence, intelligenceError, audit } = workspace;
  const decision = incident.decisions.find((item) => item.status === "PENDING") ?? [...incident.decisions].sort((a, b) => b.current_version - a.current_version)[0] ?? null;
  const decisionFinal = decision?.status === "APPROVED" || decision?.status === "REJECTED";
  const version = decisionDetail?.versions.find((item) => item.version_number === decision?.current_version) ?? null;
  const previousVersion = decisionDetail?.versions.find((item) => item.version_number === (decision?.current_version ?? 0) - 1) ?? null;
  const remainingMs = decision ? parseApiDate(decision.deadline).getTime() - Date.now() : null;
  const simulatedCount = incident.evidence.filter((item) => item.is_simulated).length;
  const verificationCount = incident.evidence.filter((item) => item.state !== "KNOWN").length;
  const results = new Map((intelligence?.ranking.results ?? []).map((item) => [item.evidence_id, item]));
  const profiles = [...(intelligence?.profiles ?? [])].sort((a, b) => (results.get(a.evidence_id)?.rank ?? 999) - (results.get(b.evidence_id)?.rank ?? 999));
  const best = profiles.find((item) => results.get(item.evidence_id)?.selected);
  const visibleGaps = (intelligence?.gaps ?? []).filter((gap, index, all) =>
    all.findIndex((item) => item.evidence_id === gap.evidence_id) === index,
  );
  const edges = (intelligence?.graph ?? []) as GraphEdge[];
  const nodeLabel = (node: string) => incident.evidence.find((item) => item.id === node)?.code.replaceAll("_", " ") ?? intelligence?.profiles.find((item) => item.evidence_id === node)?.candidate_name ?? intelligence?.hypotheses.find((item) => item.code === node)?.title ?? node;

  return <div className="app-shell">
    <a className="skip-link" href="#workspace">Skip to content</a>
    <aside className="sidebar" aria-label="Primary navigation">
      <Link className="brand" href="/cases"><span className="logo-mark"><Drop size={19} weight="fill" aria-hidden="true" /></span><span className="brand-name"><span>Aqua</span><span>Pass</span></span></Link>
      <p className="nav-caption">WORKSPACE</p>
      <nav className="primary-nav" aria-label="Workspace navigation">
        <Link className="nav-item" href="/cases"><SquaresFour size={19} weight="regular" aria-hidden="true" /><span>Cases</span></Link>
        <span className="nav-group">CURRENT CASE</span>
        {(Object.keys(sectionNames) as CaseSection[]).map((item) => { const Icon = sectionIcons[item]; return <Link key={item} className={item === section ? "nav-item nav-item-active" : "nav-item"} href={pagePath(id, item)} aria-current={item === section ? "page" : undefined}><Icon size={19} weight="regular" aria-hidden="true" /><span>{sectionNames[item]}</span></Link>; })}
      </nav>
      <div className="sidebar-bottom"><span>CASE ID</span><strong>{incident.id.slice(0, 8).toUpperCase()}</strong></div>
    </aside>

    <main className="main-content" id="workspace">
      <header className="topbar"><div className="breadcrumb"><Link href="/cases">Cases</Link><span aria-hidden="true">/</span><Link href={`/incidents/${id}`}>{incident.title}</Link><span aria-hidden="true">/</span><strong>{sectionNames[section]}</strong></div><span className="topbar-meta">AquaPass <span aria-hidden="true">/</span> Operations</span></header>
      <div className="workspace">
        <div className="case-heading"><div><p className="overline"><span>{incident.status.replaceAll("_", " ")}</span><span aria-hidden="true">·</span><span className="priority">{incident.severity} priority</span></p><h1>{incident.title}</h1><p><MapPin size={16} aria-hidden="true" /> {incident.location_name}<span aria-hidden="true">·</span> Occurred {formatDate(incident.occurred_at)} ICT</p></div><div className="deadline-box"><span>{decisionFinal ? "DECISION STATUS" : "DECISION DEADLINE"}</span><strong>{decisionFinal ? decision.status : remainingMs === null ? "—" : remainingMs <= 0 ? "Passed" : Math.ceil(remainingMs / 3_600_000) + "h"}</strong><small>{decisionFinal ? `Version ${decision.current_version} · reviewed` : decision ? formatDate(decision.deadline) + " ICT" : "No deadline"}</small></div></div>
        {(simulatedCount > 0 || intelligenceError) && <div className={intelligenceError ? "inline-alert" : "notice-bar"} role={intelligenceError ? "alert" : "status"}><Info size={18} aria-hidden="true" /><span>{intelligenceError ? `Intelligence unavailable: ${intelligenceError}` : <><strong>Simulated source data</strong> · {simulatedCount} of {incident.evidence.length} evidence records are labelled as simulated.</>}</span></div>}

        {section === "decision" && <div className="section-layout"><div className="section-main">
          <section className="decision-focus" aria-labelledby="decision-question"><div className="decision-main"><p className="eyebrow">{decisionFinal ? "DECISION REVIEWED" : "DECISION UNDER REVIEW"}</p><h2 id="decision-question">{decision?.question ?? "No decision question has been recorded."}</h2><p>{version?.summary ?? "A decision record is needed before requesting more evidence."}</p></div><dl className="decision-facts"><div><dt>Status</dt><dd><span className={`status status-${decision?.status.toLowerCase() ?? "pending"}`}>{decision?.status ?? "Not set"}</span></dd></div><div><dt>Deadline</dt><dd>{decision ? formatDate(decision.deadline) : "Not set"}</dd></div><div><dt>Uncertainty</dt><dd>{version?.uncertainty_level ?? "Not assessed"}</dd></div><div><dt>Version</dt><dd>v{decision?.current_version ?? 0} · {version?.approval_status ?? "Not set"}</dd></div></dl></section>
          {decisionFinal ? <section className="panel"><SectionHeading eyebrow="REVIEW COMPLETE" title={`Decision ${decision.status.toLowerCase()}`} /><div className="review-complete"><p>Version {decision.current_version} was reviewed by {version?.approved_by ?? "the reviewer"}.</p><p>The decision record and supporting evidence remain available for audit.</p></div><div className="panel-footer"><Link className="link-action" href={pagePath(id, "activity")}>View activity <ArrowRight size={16} aria-hidden="true" /></Link></div></section> : <section className="panel"><SectionHeading eyebrow="NEXT STEP" title="Recommended collection" side={<Link className="link-action" href={pagePath(id, "ranking")}>View ranking <ArrowRight size={16} aria-hidden="true" /></Link>} />{best ? <div className="recommendation"><span className="recommendation-number">01</span><div><h3>{best.candidate_name}</h3><p>{results.get(best.evidence_id)?.explanation ?? best.purpose}</p><span>{best.estimated_minutes} min estimated · Cost {best.estimated_cost} units</span></div><strong>{results.get(best.evidence_id)?.score.toFixed(2)}</strong></div> : <p className="empty-state">No feasible evidence option is ranked.</p>}<div className="panel-footer"><Link className="primary-button" href={pagePath(id, "workflow")}>Open workflow <ArrowRight size={16} aria-hidden="true" /></Link></div></section>}
        </div><aside className="section-aside"><section className="rail-card"><p className="eyebrow">DECISION BRIEF</p><h2>Current context</h2><p>{incident.description}</p><div className="mini-stats"><div><strong>{incident.evidence.length}</strong><span>Evidence records</span></div><div><strong>{verificationCount}</strong><span>Need verification</span></div></div></section><section className="rail-card"><p className="eyebrow">EVIDENCE GAPS</p><h2>Still needed</h2>{visibleGaps.length ? <ul className="gap-list">{visibleGaps.slice(0, 4).map((gap) => <li key={gap.evidence_id}><strong>{gap.evidence_id.replaceAll("_", " ")}</strong><span>{gap.priority} priority</span></li>)}</ul> : <p>No open gaps returned.</p>}<Link className="link-action" href={pagePath(id, "map")}>See evidence map <ArrowRight size={15} aria-hidden="true" /></Link></section></aside></div>}

        {section === "evidence" && <div className="section-layout"><section className="panel section-main"><SectionHeading eyebrow="SOURCE RECORDS" title="Evidence on record" note="Every record shows its result, source, time and reliability." side={<span className="count-label">{incident.evidence.length} records</span>} />{incident.evidence.length ? <div className="evidence-table" role="table" aria-label="Evidence records"><div className="table-head" role="row"><span role="columnheader">Evidence</span><span role="columnheader">Result</span><span role="columnheader">State</span></div>{incident.evidence.map((item) => <div className="evidence-row" role="row" key={item.id}><div role="cell"><strong>{item.code.replaceAll("_", " ")}</strong><span>{item.source} · {formatDate(item.observed_at)} ICT</span><small>{Math.round(item.reliability_score * 100)}% reliability{item.is_simulated ? " · Simulated" : ""}</small></div><strong role="cell">{valueOf(item)}</strong><span role="cell" className={`status status-${item.state.toLowerCase().replaceAll("_", "-")}`}>{item.state.replaceAll("_", " ")}</span></div>)}</div> : <p className="empty-state">No evidence attached to this incident.</p>}</section><aside className="section-aside"><section className="rail-card"><p className="eyebrow">REVIEW SIGNAL</p><h2>{verificationCount} records need verification</h2><p>Check observation time, source and recorded reliability before using them for a decision.</p></section><section className="rail-card"><p className="eyebrow">NEXT</p><h2>Relationships</h2><p>See which evidence links to each working hypothesis.</p><Link className="link-action" href={pagePath(id, "map")}>Open evidence map <ArrowRight size={15} aria-hidden="true" /></Link></section></aside></div>}

        {section === "map" && <div className="section-layout"><section className="panel section-main"><SectionHeading eyebrow="EVIDENCE RELATIONSHIPS" title="Evidence map" note="Trace the evidence behind each hypothesis and open gap." side={<span className="count-label">{edges.length} links</span>} />{edges.length ? <ul className="relationship-list">{edges.map((edge) => <li key={edge.graph_id}><div><strong>{nodeLabel(edge.source_node)}</strong><ArrowRight size={17} aria-hidden="true" /><strong>{nodeLabel(edge.target_node)}</strong></div><p><span className={`status status-${edge.state.toLowerCase().replaceAll("_", "-")}`}>{edge.state}</span> {edge.relationship.replaceAll("_", " ")} · {edge.rationale}</p></li>)}</ul> : <p className="empty-state">No relationships configured for this incident.</p>}</section><aside className="section-aside"><section className="rail-card"><p className="eyebrow">WORKING HYPOTHESES</p><h2>Current interpretation</h2>{intelligence?.hypotheses.length ? <ul className="hypothesis-list">{intelligence.hypotheses.map((item) => <li key={item.id}><div><strong>{item.code} · {item.title}</strong><span>{item.status.replaceAll("_", " ")}</span></div><b>{Math.round(item.support_score * 100)}%</b><div className="support-bar" role="img" aria-label={`${item.code} prototype support score ${Math.round(item.support_score * 100)} percent`}><span style={{ width: `${Math.round(item.support_score * 100)}%` }} /></div></li>)}</ul> : <p>No hypotheses recorded.</p>}<p className="method-note">Support is a prototype index, not a causal probability.</p></section><section className="rail-card"><p className="eyebrow">OPEN GAPS</p><h2>Missing evidence</h2>{visibleGaps.length ? <ul className="gap-list">{visibleGaps.map((gap) => <li key={gap.evidence_id}><strong>{gap.evidence_id.replaceAll("_", " ")}</strong><span>{gap.reason}</span></li>)}</ul> : <p>No open gaps returned.</p>}</section></aside></div>}

        {section === "ranking" && <div className="section-layout"><section className="panel section-main"><SectionHeading eyebrow="DECISION-VALUE RANKING" title="Evidence options" note="Feasibility, reliability, cost and time are considered against the decision deadline." side={<span className="count-label">Prototype model</span>} />{profiles.length ? <ol className="ranking-list">{profiles.map((profile) => { const result = results.get(profile.evidence_id); return <li key={profile.evidence_id} className={result?.selected ? "candidate candidate-top" : "candidate"}><span className="rank">{result ? String(result.rank).padStart(2, "0") : "—"}</span><div className="candidate-copy"><div><h3>{profile.candidate_name}</h3>{result?.selected && <span className="recommended">Top ranked</span>}</div><p>{result?.explanation ?? profile.infeasibility_reason ?? profile.purpose}</p>{result?.strengths.length ? <small>Strengths: {result.strengths.join(", ")}</small> : null}{result?.tradeoffs.length ? <small>Tradeoffs: {result.tradeoffs.join(", ")}</small> : null}</div><div className="candidate-facts"><strong>{result ? result.score.toFixed(2) : "—"}</strong><span>{profile.feasible ? "Feasible" : "Unavailable"}</span><small>{profile.estimated_minutes} min · {profile.estimated_cost} cost units</small></div></li>; })}</ol> : <p className="empty-state">No options configured for this incident type.</p>}<details className="method-details"><summary>How the score is calculated</summary><p>0.40 × decision value + 0.25 × reliability + 0.15 × feasibility − 0.10 × cost − 0.10 × time. Inputs and weights are prototype policy values, not validated environmental measurements.</p></details></section><aside className="section-aside"><section className="rail-card"><p className="eyebrow">{decisionFinal ? "REVIEW COMPLETE" : "COLLECTION"}</p><h2>{decisionFinal ? `Decision ${decision.status.toLowerCase()}` : "Proceed with a request"}</h2><p>{decisionFinal ? "Review the recorded decision and the actions that led to it." : "Choose an option in the workflow. The request remains a draft until a person confirms it."}</p><Link className={decisionFinal ? "link-action" : "primary-button"} href={pagePath(id, decisionFinal ? "activity" : "workflow")}>{decisionFinal ? "View activity" : "Open workflow"} <ArrowRight size={16} aria-hidden="true" /></Link></section><section className="rail-card"><p className="eyebrow">OPEN GAPS</p><h2>{visibleGaps.length} evidence gaps</h2>{visibleGaps.length ? <ul className="gap-list">{visibleGaps.map((gap) => <li key={gap.evidence_id}><strong>{gap.evidence_id.replaceAll("_", " ")}</strong><span>{gap.priority} priority</span></li>)}</ul> : <p>No open gaps returned.</p>}</section></aside></div>}

        {section === "workflow" && <div className="section-layout"><div className="section-main"><WorkflowActions incident={incident} decision={decision} decisionDetail={decisionDetail} overview={intelligence} audit={audit} /></div><aside className="section-aside"><section className="rail-card"><p className="eyebrow">DECISION RECORD</p><h2>Version history</h2>{version ? <div className="version-comparison"><div><span>{previousVersion ? `Previous · v${previousVersion.version_number}` : `Current · v${version.version_number}`}</span><p>{previousVersion?.summary ?? version.summary}</p><small>Uncertainty: {previousVersion?.uncertainty_level ?? version.uncertainty_level}</small></div>{previousVersion && <div><span>Current · v{version.version_number}</span><p>{version.summary}</p><small>Uncertainty: {version.uncertainty_level}</small></div>}</div> : <p>No version stored.</p>}</section><section className="rail-card"><p className="eyebrow">CONTROL</p><h2>Human approval</h2><p>A new field result updates the decision record. Approval remains an explicit reviewer action.</p><Link className="link-action" href={pagePath(id, "activity")}>View audit activity <ArrowRight size={15} aria-hidden="true" /></Link></section></aside></div>}

        {section === "activity" && <div className="section-layout"><section className="panel section-main"><SectionHeading eyebrow="APPEND-ONLY RECORD" title="Activity log" note="Events are recorded as the request and decision move through review." side={<span className="count-label">{audit.length} events</span>} />{audit.length ? <ol className="activity-list">{[...audit].reverse().map((item) => <li key={item.id}><span className="activity-marker" aria-hidden="true" /><div><strong>{item.event_type.replaceAll("_", " ")}</strong><p>{item.entity_type.replaceAll("_", " ")} · {item.actor_name}</p></div><time dateTime={item.created_at}>{formatDate(item.created_at)} ICT</time></li>)}</ol> : <p className="empty-state">No activity recorded yet.</p>}</section><aside className="section-aside"><section className="rail-card"><p className="eyebrow">TRACEABILITY</p><h2>Human actions stay visible</h2><p>Request changes, observation ingestion and decision approval are written to the audit trail.</p></section></aside></div>}
        <footer className="page-footer"><span>AquaPass · Decision-aware evidence orchestration</span><span>Prototype scores are labelled and human-reviewed.</span></footer>
      </div>
    </main>
  </div>;
}
