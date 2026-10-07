import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="container not-found">
      <p className="eyebrow">404</p>
      <h1 className="page__title">Page not found</h1>
      <p className="page__subtitle">That page doesn't exist.</p>
      <Link to="/" className="btn btn--primary">
        Back to home
      </Link>
    </main>
  );
}
