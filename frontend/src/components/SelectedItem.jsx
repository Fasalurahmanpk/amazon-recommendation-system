import { DOMAINS } from "../constants";
import { DomainIcon } from "./icons";

// Clearly shows the item the user picked, with a way to change it.
export default function SelectedItem({ domain, item, onClear }) {
  const noun = DOMAINS[domain].itemNoun;
  const meta = [];
  if (item.num_ratings) meta.push(`${item.num_ratings.toLocaleString()} ratings`);
  if (typeof item.price === "number") meta.push(`$${item.price.toFixed(2)}`);

  return (
    <div className="selected" aria-live="polite">
      <span className="selected__icon">
        <DomainIcon domain={domain} width={22} height={22} />
      </span>
      <div className="selected__body">
        <p className="selected__eyebrow">Selected {noun}</p>
        <p className="selected__title">{item.product_title}</p>
        {meta.length > 0 && <p className="selected__meta">{meta.join(" · ")}</p>}
      </div>
      <button type="button" className="btn btn--subtle" onClick={onClear}>
        Change
      </button>
    </div>
  );
}
