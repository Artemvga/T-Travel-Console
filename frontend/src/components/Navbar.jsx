import { useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const baseLinks = [
  { to: "/", label: "Главная" },
  { to: "/cities", label: "Информация о городе" },
  { to: "/routes", label: "Построение маршрута" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const links = user
    ? [...baseLinks, { to: "/favorites", label: "Избранное" }]
    : baseLinks;

  return (
    <header className="navbar-shell">
      <div className="navbar">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <img src="/t-travel-logo.png" alt="Т-Путешествия" className="brand-logo" />
          </span>
          <span className="brand-copy">
            <strong>Т-Путешествия</strong>
            <small>Маршруты и билеты по России</small>
          </span>
        </Link>

        <button
          type="button"
          className="burger-button"
          onClick={() => setOpen((value) => !value)}
          aria-label="Открыть меню"
        >
          ☰
        </button>

        <nav className={`navbar-links ${open ? "navbar-links-open" : ""}`}>
          <div className="navbar-links-primary">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `nav-link ${isActive ? "nav-link-active" : ""}`
                }
                onClick={() => setOpen(false)}
              >
                {link.label}
              </NavLink>
            ))}
          </div>

          <div className="navbar-links-secondary">
            <Link to="/routes" className="primary-button" onClick={() => setOpen(false)}>
              Построить маршрут
            </Link>

            <NavLink
              to="/account"
              className={({ isActive }) =>
                `account-link account-link-compact ${isActive ? "nav-link-active" : ""}`
              }
              onClick={() => setOpen(false)}
              aria-label={user ? `Открыть аккаунт ${user.username}` : "Открыть аккаунт"}
              title={user ? user.username : "Аккаунт"}
            >
              <span className="account-link-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" className="account-link-icon-svg">
                  <path
                    d="M12 12.2a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 1.8c-4 0-7 2-7 4.8 0 .7.5 1.2 1.2 1.2h11.6c.7 0 1.2-.5 1.2-1.2 0-2.8-3-4.8-7-4.8Z"
                    fill="currentColor"
                  />
                </svg>
              </span>
            </NavLink>
          </div>
        </nav>
      </div>
    </header>
  );
}
