import Link from "next/link";

export default function IncidentNotFound() {
  return <main className="not-found"><span className="eyebrow">AQUAPASS / 404</span><h1>Incident not found</h1><p>Check the incident link or return to the case list.</p><Link href="/cases">Return to cases →</Link></main>;
}
