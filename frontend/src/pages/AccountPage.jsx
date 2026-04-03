import { useEffect, useState } from "react";

import { Link } from "react-router-dom";

import { Footer } from "../components/Footer";
import { Loader } from "../components/Loader";
import { Navbar } from "../components/Navbar";
import { visuals } from "../content/visuals";
import { useAuth } from "../context/AuthContext";
import { getApiError } from "../services/api";

function formatAccountDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

function formatSearchDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function AccountPage() {
  const { user, ready, isAuthenticated, login, logout, refreshProfile, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loginForm, setLoginForm] = useState({
    username: "",
    password: "",
  });
  const [registerForm, setRegisterForm] = useState({
    username: "",
    password: "",
    password_confirm: "",
  });

  useEffect(() => {
    if (ready && isAuthenticated) {
      refreshProfile().catch(() => {});
    }
  }, [isAuthenticated, ready]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      await login(loginForm);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось выполнить вход."));
    } finally {
      setBusy(false);
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      await register(registerForm);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось зарегистрировать пользователя."));
    } finally {
      setBusy(false);
    }
  };

  if (!ready) {
    return (
      <div className="page-shell">
        <Navbar />
        <main className="page">
          <Loader text="Подключаем личный кабинет..." />
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="page-shell">
      <Navbar />

      <main className="page">
        {!isAuthenticated ? (
          <section className="content-card account-card">
            <div className="account-layout">
              <div className="account-promo">
                <p className="eyebrow">Аккаунт</p>
                <h2>Войдите, чтобы видеть последние поиски и работать с маршрутом как с личной сессией.</h2>
                <p className="page-copy">
                  Авторизация уже работает через Django API. После входа поиск маршрутов
                  привязывается к вашему профилю, а история запросов видна прямо в кабинете.
                </p>
                <div className="hero-chip-row">
                  <span className="hero-chip">Вход и регистрация</span>
                  <span className="hero-chip">История поисков</span>
                  <span className="hero-chip">Token auth</span>
                </div>
                <div className="account-promo-image">
                  <img src={visuals.rail} alt="Авторизация и профиль" />
                </div>
              </div>

              <div className="account-form-card">
                <div className="account-mode-switch">
                  <button
                    type="button"
                    className={`secondary-button ${mode === "login" ? "mode-active" : ""}`}
                    onClick={() => setMode("login")}
                  >
                    Вход
                  </button>
                  <button
                    type="button"
                    className={`secondary-button ${mode === "register" ? "mode-active" : ""}`}
                    onClick={() => setMode("register")}
                  >
                    Регистрация
                  </button>
                </div>

                {error ? <div className="inline-alert inline-alert-error">{error}</div> : null}

                {mode === "login" ? (
                  <form className="account-form" onSubmit={handleLogin}>
                    <label className="field-stack">
                      <span>Логин</span>
                      <input
                        type="text"
                        value={loginForm.username}
                        onChange={(event) =>
                          setLoginForm((current) => ({
                            ...current,
                            username: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className="field-stack">
                      <span>Пароль</span>
                      <input
                        type="password"
                        value={loginForm.password}
                        onChange={(event) =>
                          setLoginForm((current) => ({
                            ...current,
                            password: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <button type="submit" className="primary-button" disabled={busy}>
                      {busy ? "Входим..." : "Войти"}
                    </button>
                  </form>
                ) : (
                  <form className="account-form" onSubmit={handleRegister}>
                    <label className="field-stack">
                      <span>Логин</span>
                      <input
                        type="text"
                        value={registerForm.username}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            username: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className="field-stack">
                      <span>Пароль</span>
                      <input
                        type="password"
                        value={registerForm.password}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            password: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className="field-stack">
                      <span>Повтор пароля</span>
                      <input
                        type="password"
                        value={registerForm.password_confirm}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            password_confirm: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <button type="submit" className="primary-button" disabled={busy}>
                      {busy ? "Создаем..." : "Создать аккаунт"}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </section>
        ) : (
          <>
            <section className="content-card account-card">
              <div className="account-hero">
                <div>
                  <p className="eyebrow">Личный кабинет</p>
                  <h2>{user.username}, ваш профиль уже подключен к поиску маршрутов.</h2>
                  <p className="page-copy">
                    Запросы, отправленные из интерфейса под этой учетной записью,
                    сохраняются в истории и доступны на этой странице.
                  </p>
                </div>
                <div className="account-hero-actions">
                  <Link to="/routes" className="primary-button">
                    Найти маршрут
                  </Link>
                  <button type="button" className="secondary-button" onClick={logout}>
                    Выйти
                  </button>
                </div>
              </div>

              <div className="info-grid">
                <div className="mini-card">
                  <span>Пользователь</span>
                  <strong>{user.username}</strong>
                </div>
                <div className="mini-card">
                  <span>Дата регистрации</span>
                  <strong>{formatAccountDate(user.date_joined)}</strong>
                </div>
                <div className="mini-card">
                  <span>Последних поисков</span>
                  <strong>{user.recent_searches?.length || 0}</strong>
                </div>
              </div>
            </section>

            <section className="content-card account-card">
              <div className="section-head">
                <div>
                  <p className="eyebrow">История</p>
                  <h2>Последние запросы маршрутов</h2>
                </div>
              </div>

              {user.recent_searches?.length ? (
                <div className="recent-searches-grid">
                  {user.recent_searches.map((item) => (
                    <article key={item.id} className="mini-card recent-search-card">
                      <span>
                        {item.from_city} → {item.to_city}
                      </span>
                      <strong>
                        {item.via_city ? `Через ${item.via_city}` : "Без обязательного транзита"}
                      </strong>
                      <p>
                        Приоритет: {item.priority_mode} • {formatSearchDate(item.created_at)}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="page-copy">
                  Пока нет сохраненных поисков. Постройте первый маршрут, и он сразу появится здесь.
                </p>
              )}
            </section>
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}
