import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle,
  Drop,
  MapPinLine,
  ShieldCheck,
  Waves,
} from "@phosphor-icons/react/dist/ssr";

const projectSteps = [
  {
    number: "01",
    title: "Observe",
    description: "Bring field reports, sensor readings and local conditions into one case.",
    icon: MapPinLine,
  },
  {
    number: "02",
    title: "Understand",
    description: "See what is known, what is uncertain and which evidence is still missing.",
    icon: Waves,
  },
  {
    number: "03",
    title: "Coordinate",
    description: "Route a useful next step and keep a clear record for human review.",
    icon: ShieldCheck,
  },
];

function EarthIllustration() {
  return (
    <svg
      className="earth-illustration"
      viewBox="0 0 600 600"
      role="img"
      aria-labelledby="earth-title earth-description"
    >
      <title id="earth-title">Illustrated view of Earth focused on water and connected ecosystems</title>
      <desc id="earth-description">
        A calm blue globe with mapped continents, latitude lines and a field observation marker.
      </desc>
      <defs>
        <linearGradient id="ocean" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#d9f0eb" />
          <stop offset="0.56" stopColor="#9dcfd0" />
          <stop offset="1" stopColor="#72acb2" />
        </linearGradient>
        <linearGradient id="globe-shadow" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.5" />
          <stop offset="1" stopColor="#254f68" stopOpacity="0.2" />
        </linearGradient>
        <clipPath id="globe-clip">
          <circle cx="300" cy="300" r="216" />
        </clipPath>
      </defs>
      <circle cx="300" cy="300" r="232" fill="#ffffff" opacity="0.55" />
      <circle cx="300" cy="300" r="216" fill="url(#ocean)" />
      <g clipPath="url(#globe-clip)">
        <g fill="none" stroke="#f5ffff" strokeOpacity="0.53" strokeWidth="1.3">
          <ellipse cx="300" cy="300" rx="104" ry="216" />
          <ellipse cx="300" cy="300" rx="176" ry="216" />
          <ellipse cx="300" cy="300" rx="216" ry="68" />
          <ellipse cx="300" cy="300" rx="216" ry="142" />
          <path d="M84 300h432M105 216h390M105 384h390" />
        </g>
        <g fill="#d6e7d2" stroke="#f4f7e9" strokeLinejoin="round" strokeWidth="2">
          <path d="m114 179 22-22 39-8 23 14 4 18-20 12-13 24-29 4-19-18-19-3z" />
          <path d="m193 215 24 4 17 20-8 24 13 21-7 31-17 21-9 41-17 29-14-26 5-39-14-26 5-35-10-21 15-22z" />
          <path d="m259 164 24-19 36 5 18 18 29-2 19 16 31-7 26 14 5 19-21 15-27-7-11 20-31-3-19 22-22-8-20 12-18-18-25-1-10-24-22-12 4-22-15-12z" />
          <path d="m337 264 29 7 21 21-8 22 13 25-10 36-20 27-8 35-19 10-18-24 2-27-12-23 12-34-7-27z" />
          <path d="m443 361 28 8 21 20-12 21-28-4-18-17z" />
          <path d="m152 130 16-8 11 8-7 13-18 2zM425 151l18-5 15 9-3 12-20 4-15-9z" />
        </g>
        <circle cx="300" cy="300" r="216" fill="url(#globe-shadow)" />
        <path d="M107 221c49-79 126-123 211-134" fill="none" stroke="#ffffff" strokeOpacity="0.72" strokeWidth="9" strokeLinecap="round" />
      </g>
      <circle cx="421" cy="259" r="17" fill="#f9f7e9" opacity="0.92" />
      <circle cx="421" cy="259" r="8" fill="#c46e4c" />
      <circle cx="421" cy="259" r="25" fill="none" stroke="#fbfaf2" strokeOpacity="0.78" strokeWidth="1.5" />
      <path d="M441 247c23-17 44-22 64-20" fill="none" stroke="#a85a40" strokeWidth="1.5" strokeDasharray="3 5" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <main className="intro-page">
      <a className="intro-skip-link" href="#project">
        Skip to project introduction
      </a>
      <header className="intro-header">
        <Link className="intro-brand" href="/" aria-label="AquaPass home">
          <span className="intro-brand-mark">
            <Drop size={19} weight="fill" aria-hidden="true" />
          </span>
          <span className="intro-brand-name">AquaPass</span>
        </Link>
        <nav className="intro-nav" aria-label="Main navigation">
          <a href="#project">The project</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <Link className="intro-header-link" href="/cases">
          Open workspace <ArrowUpRight size={16} aria-hidden="true" />
        </Link>
      </header>

      <section className="intro-hero" id="project" aria-labelledby="intro-title">
        <div className="intro-copy">
          <p className="intro-kicker"><span /> WATER HEALTH · ONE HEALTH</p>
          <h1 id="intro-title">
            See the whole picture.<br />
            <em>Choose the next step.</em>
          </h1>
          <p className="intro-lede">
            AquaPass helps response teams turn scattered water-health signals into clear,
            evidence-aware decisions — with people in the loop at every step.
          </p>
          <div className="intro-actions">
            <Link className="intro-primary-button" href="/cases">
              Explore the workspace <ArrowRight size={18} aria-hidden="true" />
            </Link>
            <a className="intro-text-link" href="#how-it-works">
              Get to know the project <span aria-hidden="true">↓</span>
            </a>
          </div>
          <div className="intro-principles" aria-label="Project principles">
            <span><CheckCircle size={17} aria-hidden="true" /> Evidence with context</span>
            <span><CheckCircle size={17} aria-hidden="true" /> Decisions reviewed by people</span>
          </div>
        </div>

        <div className="earth-stage" aria-label="AquaPass field research illustration">
          <div className="earth-orbit earth-orbit-one" aria-hidden="true" />
          <div className="earth-orbit earth-orbit-two" aria-hidden="true" />
          <span className="earth-stage-index">FIELD ATLAS <span>·</span> 01</span>
          <EarthIllustration />

          <aside className="field-note field-note-top">
            <span className="note-label">FIELD NOTE / 01</span>
            <strong>Start with the place.</strong>
            <span className="note-rule" />
            <small>Water connects what a map keeps apart.</small>
          </aside>

          <aside className="field-note field-note-pin">
            <span className="pin-dot" aria-hidden="true" />
            <span className="note-label">OBSERVATION SITE</span>
            <strong>One watershed</strong>
            <small>Many signals · shared response</small>
          </aside>

          <div className="earth-caption"><span>01</span> A living system, seen from many sides</div>
          <div className="earth-coordinates">10°46′37″N<br />106°42′03″E</div>
        </div>
      </section>

      <section className="intro-method" id="how-it-works" aria-labelledby="method-title">
        <div className="method-heading">
          <p className="intro-kicker"><span /> FROM SIGNAL TO RESPONSE</p>
          <h2 id="method-title">A clearer path through uncertainty.</h2>
          <p>Every case keeps its evidence, gaps and next actions connected.</p>
        </div>
        <div className="method-steps">
          {projectSteps.map(({ number, title, description, icon: Icon }) => (
            <article className="method-step" key={number}>
              <div className="method-step-top"><span>{number}</span><Icon size={21} weight="regular" aria-hidden="true" /></div>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="intro-footer">
        <span>© AquaPass · Decision-aware evidence orchestration for One Health</span>
        <span><span className="footer-status-dot" /> Research prototype</span>
      </footer>
    </main>
  );
}
