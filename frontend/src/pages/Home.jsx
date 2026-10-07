import { Link } from "react-router-dom";
import Hero from "../components/Hero";
import { ArrowRightIcon, DomainIcon } from "../components/icons";

const APPROACHES = [
  {
    title: "Collaborative Filtering",
    tag: "Behaviour-based",
    text: "Learns from how people rate. Item-based neighbours surface titles that the same users rated similarly, ranked by cosine similarity.",
  },
  {
    title: "Content-Based",
    tag: "Text-based",
    text: "Turns titles, descriptions and categories into TF-IDF vectors and finds the items whose text is closest to the one you picked.",
  },
  {
    title: "Hybrid RRF",
    tag: "Best of both",
    text: "Fuses the collaborative and content rankings with weighted Reciprocal Rank Fusion, so items that rank well in either list rise to the top.",
  },
];

const DOMAIN_CARDS = [
  {
    key: "movies",
    to: "/movies",
    title: "Movies & TV",
    text: "Search a movie or show and explore what to watch next.",
  },
  {
    key: "games",
    to: "/games",
    title: "Video Games",
    text: "Search a game and find similar titles worth playing.",
  },
];

export default function Home() {
  return (
    <main>
      <Hero />

      <section className="section container">
        <header className="section__head">
          <p className="eyebrow">How it works</p>
          <h2 className="section__title">Three ways to recommend</h2>
          <p className="section__lead">
            Every method runs on the same Amazon Reviews 2023 data, so you can
            compare how each one sees the catalog.
          </p>
        </header>
        <div className="approach-grid">
          {APPROACHES.map((approach, index) => (
            <article className="approach" key={approach.title}>
              <span className="approach__index">0{index + 1}</span>
              <p className="approach__tag">{approach.tag}</p>
              <h3 className="approach__title">{approach.title}</h3>
              <p className="approach__text">{approach.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section container">
        <header className="section__head">
          <p className="eyebrow">Get started</p>
          <h2 className="section__title">Pick a domain</h2>
        </header>
        <div className="domain-grid">
          {DOMAIN_CARDS.map((card) => (
            <Link
              to={card.to}
              key={card.key}
              className="domain-card"
              data-domain={card.key}
            >
              <span className="domain-card__icon">
                <DomainIcon domain={card.key} width={24} height={24} />
              </span>
              <span className="domain-card__body">
                <span className="domain-card__title">{card.title}</span>
                <span className="domain-card__text">{card.text}</span>
              </span>
              <ArrowRightIcon className="domain-card__arrow" />
            </Link>
          ))}
        </div>
      </section>

      <section className="section container">
        <div className="architecture" aria-label="Architecture overview">
          <span>React UI</span>
          <i aria-hidden="true">→</i>
          <span>FastAPI</span>
          <i aria-hidden="true">→</i>
          <span>Recommendation models</span>
        </div>
      </section>
    </main>
  );
}
