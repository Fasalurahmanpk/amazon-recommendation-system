import { useEffect, useState } from "react";

// Skeleton cards + a hint when the first request is slow (model warm-up).
export default function LoadingState({ message = "Finding recommendations..." }) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="loading" role="status" aria-live="polite">
      <div className="loading__head">
        <span className="spinner spinner--lg" aria-hidden="true" />
        <div>
          <p className="loading__title">{message}</p>
          {slow && (
            <p className="loading__hint">
              This is taking a little longer than usual. The first request for a
              catalog loads its models into memory, and later requests are much
              faster.
            </p>
          )}
        </div>
      </div>
      <div className="grid" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => (
          <div className="rec-card rec-card--skeleton" key={index}>
            <span className="skeleton skeleton--short" />
            <span className="skeleton skeleton--title" />
            <span className="skeleton skeleton--title skeleton--half" />
            <span className="skeleton skeleton--bar" />
          </div>
        ))}
      </div>
    </div>
  );
}
