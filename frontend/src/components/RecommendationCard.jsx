import { DOMAINS, METHOD_BY_KEY, SCORE_META } from "../constants";
import { DomainIcon } from "./icons";

function rankLabel(rank) {
  return rank ? `#${rank}` : "-";
}

export default function RecommendationCard({ item, domain, relativeScore, index }) {
  const scoreMeta = SCORE_META[item.method] || SCORE_META.hybrid;
  const method = METHOD_BY_KEY[item.method];
  const details = item.details;
  const percent = Math.max(4, Math.round((relativeScore || 0) * 100));
  const meta = [];
  if (typeof item.price === "number") meta.push(`$${item.price.toFixed(2)}`);
  if (item.num_ratings) meta.push(`${item.num_ratings.toLocaleString()} ratings`);

  return (
    <article
      className="rec-card"
      style={{ animationDelay: `${Math.min(index, 12) * 45}ms` }}
    >
      <div className="rec-card__top">
        <span className="rec-card__rank" aria-label={`Rank ${item.rank}`}>
          {String(item.rank).padStart(2, "0")}
        </span>
        <span className="badge">{method ? method.short : item.method}</span>
      </div>

      <h3 className="rec-card__title" title={item.product_title}>
        {item.product_title}
      </h3>

      <p className="rec-card__domain">
        <DomainIcon domain={domain} width={15} height={15} />
        {DOMAINS[domain].cardTag}
      </p>

      <div className="score">
        <div className="score__row">
          <span className="score__label" title={scoreMeta.hint}>
            {scoreMeta.label}
          </span>
          <span className="score__value">
            {typeof item.score === "number"
              ? item.score.toFixed(scoreMeta.digits)
              : "-"}
          </span>
        </div>
        <div
          className="score__bar"
          title="Length relative to the top result in this list"
        >
          <span style={{ width: `${percent}%` }} />
        </div>
      </div>

      {details && (
        <ul className="chips" aria-label="Ranks in each underlying model">
          <li title="Rank in the collaborative-filtering candidate list">
            CF {rankLabel(details.cf_rank)}
          </li>
          <li title="Rank in the content-based candidate list">
            Content {rankLabel(details.content_rank)}
          </li>
        </ul>
      )}

      {meta.length > 0 && <p className="rec-card__meta">{meta.join(" · ")}</p>}
    </article>
  );
}
