import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DOMAINS } from "../constants";
import { getRecommendations } from "../services/recommendationApi";
import DomainSelector from "../components/DomainSelector";
import SearchBar from "../components/SearchBar";
import SelectedItem from "../components/SelectedItem";
import RecommendationMethod from "../components/RecommendationMethod";
import RecommendationGrid from "../components/RecommendationGrid";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { SparkIcon } from "../components/icons";

// Shared experience for Movies & TV and Video Games.
export default function RecommenderPage({ domain }) {
  const config = DOMAINS[domain];
  const navigate = useNavigate();

  const [selected, setSelected] = useState(null);
  const [method, setMethod] = useState("hybrid");
  const [phase, setPhase] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const requestRef = useRef(null);
  const resultsRef = useRef(null);

  // Cancel any in-flight request when leaving the page.
  useEffect(() => () => requestRef.current?.abort(), []);

  // Bring the results area into view as soon as a request starts / finishes.
  useEffect(() => {
    if (phase !== "idle") {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [phase]);

  const reset = useCallback(() => {
    requestRef.current?.abort();
    setSelected(null);
    setResult(null);
    setError(null);
    setPhase("idle");
  }, []);

  const run = useCallback(async () => {
    if (!selected) return;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;

    setPhase("loading");
    setError(null);
    try {
      const data = await getRecommendations(domain, {
        itemId: selected.item_id,
        method,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setResult(data);
      setPhase("success");
    } catch (err) {
      if (err.name === "AbortError") return;
      setError(err);
      setPhase("error");
    }
  }, [domain, selected, method]);

  const loading = phase === "loading";

  return (
    <main className="page" data-domain={domain}>
      <div className="page__glow" aria-hidden="true" />

      <section className="container page__head">
        <DomainSelector
          active={domain}
          onChange={(key) => navigate(DOMAINS[key].path)}
        />
        <h1 className="page__title">{config.title}</h1>
        <p className="page__subtitle">{config.subtitle}</p>
      </section>

      <section className="container">
        <div className="panel">
          <div className="panel__step">
            <span className="step-number">1</span>
            <div className="panel__content">
              {selected ? (
                <>
                  <p className="field-label">Your {config.itemNoun}</p>
                  <SelectedItem
                    domain={domain}
                    item={selected}
                    onClear={reset}
                  />
                </>
              ) : (
                <SearchBar
                  domain={domain}
                  onSelect={(item) => {
                    setSelected(item);
                    setResult(null);
                    setError(null);
                    setPhase("idle");
                  }}
                />
              )}
            </div>
          </div>

          <div className="panel__step">
            <span className="step-number">2</span>
            <div className="panel__content">
              <RecommendationMethod
                value={method}
                onChange={setMethod}
                disabled={loading}
              />
            </div>
          </div>

          <div className="panel__actions">
            <button
              type="button"
              className="btn btn--primary btn--lg"
              onClick={run}
              disabled={!selected || loading}
            >
              <SparkIcon />
              {loading ? "Finding recommendations..." : "Get Recommendations"}
            </button>
            {(selected || result) && (
              <button type="button" className="btn btn--ghost" onClick={reset}>
                New search
              </button>
            )}
            {!selected && (
              <span className="panel__hint">
                Select a {config.itemNoun} to enable recommendations.
              </span>
            )}
          </div>
        </div>
      </section>

      <section className="container results" ref={resultsRef}>
        {phase === "loading" && <LoadingState />}
        {phase === "error" && <ErrorState error={error} onRetry={run} />}
        {phase === "success" && result && (
          <RecommendationGrid result={result} domain={domain} />
        )}
      </section>
    </main>
  );
}
