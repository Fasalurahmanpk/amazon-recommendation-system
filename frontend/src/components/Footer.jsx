export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <p>
          <strong>RecomAI</strong> - a machine-learning recommendation demo built on
          the Amazon Reviews 2023 dataset.
        </p>
        <p className="footer__stack">React · FastAPI · scikit-learn</p>
      </div>
    </footer>
  );
}
