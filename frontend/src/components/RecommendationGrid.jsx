import { METHOD_BY_KEY } from "../constants";
import RecommendationCard from "./RecommendationCard";
import { InfoIcon } from "./icons";

export default function RecommendationGrid({ result, domain }) {
  const items = result.recommendations;
  const topScore = items.reduce((max, item) => Math.max(max, item.score || 0), 0);
  const usedMethod = METHOD_BY_KEY[result.method_used];
  const seconds = (result.elapsed_ms / 1000).toFixed(result.elapsed_ms < 1000 ? 2 : 1);

  return (
    <div className="grid-section">
      <header className="grid-section__head">
        <div>
          <p className="eyebrow">Recommended for you</p>
          <h2 className="grid-section__title">
            Because you picked{" "}
            <span className="gradient-text">{result.source_item.product_title}</span>
          </h2>
        </div>
        <ul className="meta-pills">
          <li>{usedMethod ? usedMethod.label : result.method_used}</li>
          <li>{result.count} results</li>
          <li>{seconds}s</li>
        </ul>
      </header>

      {result.message && (
        <p className="notice" role="status">
          <InfoIcon /> {result.message}
        </p>
      )}

      {items.length === 0 ? (
        <div className="empty">
          <p className="empty__title">No recommendations found</p>
          <p className="empty__text">
            This item doesn't have enough data for the selected method. Try another
            method or pick a different title.
          </p>
        </div>
      ) : (
        <div className="grid">
          {items.map((item, index) => (
            <RecommendationCard
              key={item.item_id}
              item={item}
              domain={domain}
              index={index}
              relativeScore={topScore ? (item.score || 0) / topScore : 0}
            />
          ))}
        </div>
      )}

      <p className="grid-section__footnote">
        Scores are method-specific ranking signals (similarity or rank fusion), not
        probabilities, and aren't comparable across methods.
      </p>
    </div>
  );
}
