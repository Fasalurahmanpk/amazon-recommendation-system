import { Link } from "react-router-dom";
import { ArrowRightIcon } from "./icons";

export default function Hero() {
  return (
    <section className="hero">
      <div className="hero__glow" aria-hidden="true" />
      <div className="hero__grid" aria-hidden="true" />
      <div className="container hero__inner">
        <p className="eyebrow">RecomAI</p>
        <h1 className="hero__title">
          Discover Your <span className="gradient-text">Next Favorite</span>
        </h1>
        <p className="hero__subtitle">
          Personalized movie and game recommendations powered by machine learning.
        </p>
        <div className="hero__actions">
          <Link to="/movies" className="btn btn--primary">
            Explore Movies <ArrowRightIcon />
          </Link>
          <Link to="/games" className="btn btn--ghost">
            Explore Games <ArrowRightIcon />
          </Link>
        </div>
        <ul className="hero__facts" aria-label="Project facts">
          <li>Amazon Reviews 2023</li>
          <li>Movies &amp; Video Games</li>
          <li>Three recommendation methods</li>
        </ul>
      </div>
    </section>
  );
}
