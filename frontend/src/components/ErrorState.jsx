import { AlertIcon } from "./icons";

const TITLES = {
  network: "Can't reach the API",
  timeout: "The request timed out",
  not_found: "Item not found",
  validation: "Invalid request",
  unavailable: "This method isn't available right now",
  server: "Something went wrong",
};

const HINTS = {
  network:
    "Start the backend from the project root with: python -m uvicorn backend.main:app --reload",
  unavailable:
    "The model needs more free memory than is currently available. Try Content-Based or another method, or close other applications and retry.",
};

export default function ErrorState({ error, onRetry }) {
  const kind = (error && error.kind) || "server";
  const message =
    (error && error.message) || "An unexpected error occurred. Please try again.";

  return (
    <div className="error-state" role="alert">
      <span className="error-state__icon">
        <AlertIcon width={22} height={22} />
      </span>
      <div className="error-state__body">
        <p className="error-state__title">{TITLES[kind] || TITLES.server}</p>
        <p className="error-state__text">{message}</p>
        {HINTS[kind] && <p className="error-state__hint">{HINTS[kind]}</p>}
      </div>
      {onRetry && (
        <button type="button" className="btn btn--subtle" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
