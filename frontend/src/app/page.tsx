import Link from "next/link";
import Image from "next/image";
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
          <span className="intro-brand-name"><span>Aqua</span><span>Pass</span></span>
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

        <div className="earth-stage">
          <div className="earth-orbit earth-orbit-one" aria-hidden="true" />
          <div className="earth-orbit earth-orbit-two" aria-hidden="true" />
          <span className="earth-stage-index">ONE HEALTH <span>·</span> A SHARED PLANET</span>
          <div className="earth-photo-frame">
            <Image
              className="earth-photo"
              src="/images/earth-apollo-17.jpg"
              alt="Earth photographed by the Apollo 17 crew, with Africa, clouds and Antarctica visible"
              width={1024}
              height={1024}
              sizes="(max-width: 740px) 90vw, 500px"
              priority
            />
          </div>

          <aside className="field-note field-note-top">
            <span className="note-label">FIELD NOTE / 01</span>
            <strong>Start with the place.</strong>
            <span className="note-rule" />
            <small>Water connects what a map keeps apart.</small>
          </aside>

          <aside className="field-note field-note-pin">
            <span className="pin-dot" aria-hidden="true" />
            <span className="note-label">ONE HEALTH VIEW</span>
            <strong>One connected system</strong>
            <small>Water · people · ecosystems</small>
          </aside>

          <div className="earth-caption">A living system, seen from many sides</div>
          <a className="earth-photo-credit" href="https://svs.gsfc.nasa.gov/30613/">
            Photo: NASA / Apollo 17 <ArrowUpRight size={12} aria-hidden="true" />
          </a>
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
