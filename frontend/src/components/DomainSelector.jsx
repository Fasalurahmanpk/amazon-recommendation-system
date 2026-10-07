import { DOMAIN_LIST } from "../constants";
import { DomainIcon } from "./icons";

// Segmented switch between Movies & TV and Video Games.
export default function DomainSelector({ active, onChange }) {
  return (
    <div className="segmented" role="tablist" aria-label="Choose a domain">
      {DOMAIN_LIST.map((domain) => {
        const selected = domain.key === active;
        return (
          <button
            key={domain.key}
            type="button"
            role="tab"
            aria-selected={selected}
            className={`segmented__item ${selected ? "is-active" : ""}`}
            onClick={() => !selected && onChange(domain.key)}
          >
            <DomainIcon domain={domain.key} />
            {domain.navLabel}
          </button>
        );
      })}
    </div>
  );
}
