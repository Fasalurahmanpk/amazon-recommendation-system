import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import Logo from "./Logo";
import { CloseIcon, MenuIcon } from "./icons";
import useApiHealth from "../hooks/useApiHealth";

const LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/movies", label: "Movies & TV" },
  { to: "/games", label: "Video Games" },
];

const STATUS_LABEL = {
  checking: "Checking API",
  online: "API online",
  offline: "API offline",
};

export default function Header() {
  const [open, setOpen] = useState(false);
  const health = useApiHealth();
  const close = () => setOpen(false);

  return (
    <header className="header">
      <div className="container header__inner">
        <Link to="/" className="brand" onClick={close} aria-label="RecomAI home">
          <Logo size={30} />
          <span className="brand__name">
            Recom<b>AI</b>
          </span>
        </Link>

        <nav
          id="primary-nav"
          className={`nav ${open ? "nav--open" : ""}`}
          aria-label="Primary"
        >
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={close}
              className={({ isActive }) =>
                `nav__link ${isActive ? "is-active" : ""}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="header__right">
          <span
            className={`status status--${health}`}
            title={STATUS_LABEL[health]}
            role="status"
          >
            <i aria-hidden="true" />
            <span className="status__text">{STATUS_LABEL[health]}</span>
          </span>
          <button
            type="button"
            className="menu-toggle"
            aria-expanded={open}
            aria-controls="primary-nav"
            aria-label={open ? "Close navigation" : "Open navigation"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>
    </header>
  );
}
