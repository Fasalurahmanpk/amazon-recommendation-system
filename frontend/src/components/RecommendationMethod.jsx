import { METHODS } from "../constants";

// Radio-card selector for the recommendation method.
export default function RecommendationMethod({ value, onChange, disabled }) {
  return (
    <fieldset className="methods" disabled={disabled}>
      <legend className="field-label">Recommendation method</legend>
      <div className="methods__grid">
        {METHODS.map((method) => (
          <label
            key={method.key}
            className={`method ${value === method.key ? "is-active" : ""}`}
          >
            <input
              type="radio"
              name="method"
              value={method.key}
              checked={value === method.key}
              onChange={() => onChange(method.key)}
            />
            <span className="method__label">{method.label}</span>
            <span className="method__desc">{method.description}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
