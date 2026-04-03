import { useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/", label: "Главная" },
  { to: "/cities", label: "Информация о городе" },
  { to: "/routes", label: "Построение маршрута" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const avatarLabel = user?.username?.slice(0, 1)?.toUpperCase() || "◌";

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
          <NavLink
            to="/account"
            className={({ isActive }) =>
              `account-link ${isActive ? "nav-link-active" : ""}`
            }
            onClick={() => setOpen(false)}
            aria-label="Открыть аккаунт"
          >
            <span className="account-link-icon">{avatarLabel}</span>
            <span className="account-link-copy">
              <strong>{user?.username || "Аккаунт"}</strong>
              <small>{user ? "Личный кабинет" : "Войти"}</small>
            </span>
          </NavLink>
          <Link to="/routes" className="primary-button" onClick={() => setOpen(false)}>
            Построить маршрут
          </Link>
        </nav>
      </div>
    </header>
  );
}
