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
  const [loginInvalid, setLoginInvalid] = useState({
    username: false,
    password: false,
  });
  const [registerInvalid, setRegisterInvalid] = useState({
    username: false,
    password: false,
    password_confirm: false,
  });
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
    setLoginInvalid({
      username: false,
      password: false,
    });

    try {
      await login(loginForm);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось выполнить вход."));
      setLoginInvalid({
        username: true,
        password: true,
      });
    } finally {
      setBusy(false);
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setRegisterInvalid({
      username: false,
      password: false,
      password_confirm: false,
    });

    try {
      await register(registerForm);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось зарегистрировать пользователя."));
      const data = requestError?.response?.data || {};
      setRegisterInvalid({
        username: Boolean(data.username),
        password: Boolean(data.password),
        password_confirm: Boolean(data.password_confirm),
      });
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
          <section className="content-card account-card account-card-guest">
            <div className="account-layout">
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

                {error ? (
                  <div className="inline-alert inline-alert-error" role="alert">
                    {error}
                  </div>
                ) : null}

                {mode === "login" ? (
                  <form className="account-form" onSubmit={handleLogin}>
                    <label className={`field-stack ${loginInvalid.username ? "field-stack-error" : ""}`}>
                      <span>Логин</span>
                      <input
                        type="text"
                        aria-invalid={loginInvalid.username}
                        value={loginForm.username}
                        onChange={(event) =>
                          {
                            setError("");
                            setLoginInvalid((current) => ({ ...current, username: false }));
                            setLoginForm((current) => ({
                              ...current,
                              username: event.target.value,
                            }));
                          }
                        }
                      />
                      {loginInvalid.username ? (
                        <small className="field-error-note">Проверьте логин.</small>
                      ) : null}
                    </label>
                    <label className={`field-stack ${loginInvalid.password ? "field-stack-error" : ""}`}>
                      <span>Пароль</span>
                      <input
                        type="password"
                        aria-invalid={loginInvalid.password}
                        value={loginForm.password}
                        onChange={(event) =>
                          {
                            setError("");
                            setLoginInvalid((current) => ({ ...current, password: false }));
                            setLoginForm((current) => ({
                              ...current,
                              password: event.target.value,
                            }));
                          }
                        }
                      />
                      {loginInvalid.password ? (
                        <small className="field-error-note">Проверьте пароль.</small>
                      ) : null}
                    </label>
                    <button type="submit" className="primary-button" disabled={busy}>
                      {busy ? "Входим..." : "Войти"}
                    </button>
                  </form>
                ) : (
                  <form className="account-form" onSubmit={handleRegister}>
                    <label className={`field-stack ${registerInvalid.username ? "field-stack-error" : ""}`}>
                      <span>Логин</span>
                      <input
                        type="text"
                        aria-invalid={registerInvalid.username}
                        value={registerForm.username}
                        onChange={(event) =>
                          {
                            setError("");
                            setRegisterInvalid((current) => ({ ...current, username: false }));
                            setRegisterForm((current) => ({
                              ...current,
                              username: event.target.value,
                            }));
                          }
                        }
                      />
                      {registerInvalid.username ? (
                        <small className="field-error-note">Логин уже занят или заполнен неверно.</small>
                      ) : null}
                    </label>
                    <label className={`field-stack ${registerInvalid.password ? "field-stack-error" : ""}`}>
                      <span>Пароль</span>
                      <input
                        type="password"
                        aria-invalid={registerInvalid.password}
                        value={registerForm.password}
                        onChange={(event) =>
                          {
                            setError("");
                            setRegisterInvalid((current) => ({ ...current, password: false }));
                            setRegisterForm((current) => ({
                              ...current,
                              password: event.target.value,
                            }));
                          }
                        }
                      />
                      {registerInvalid.password ? (
                        <small className="field-error-note">Пароль не подходит.</small>
                      ) : null}
                    </label>
                    <label className={`field-stack ${registerInvalid.password_confirm ? "field-stack-error" : ""}`}>
                      <span>Повтор пароля</span>
                      <input
                        type="password"
                        aria-invalid={registerInvalid.password_confirm}
                        value={registerForm.password_confirm}
                        onChange={(event) =>
                          {
                            setError("");
                            setRegisterInvalid((current) => ({
                              ...current,
                              password_confirm: false,
                            }));
                            setRegisterForm((current) => ({
                              ...current,
                              password_confirm: event.target.value,
                            }));
                          }
                        }
                      />
                      {registerInvalid.password_confirm ? (
                        <small className="field-error-note">Пароли должны совпадать.</small>
                      ) : null}
                    </label>
                    <button type="submit" className="primary-button" disabled={busy}>
                      {busy ? "Создаем..." : "Создать аккаунт"}
                    </button>
                  </form>
                )}
              </div>

              <div className="account-promo">
                <p className="eyebrow">Аккаунт</p>
                <h2>Войдите, чтобы открыть избранное маршрутов, историю поиска и быстрый доступ к своим поездкам.</h2>
                <p className="page-copy">
                  После входа маршруты можно сохранять в избранное, а история поисков
                  и последние найденные поездки будут доступны в одном личном кабинете.
                </p>
                <div className="hero-chip-row">
                  <span className="hero-chip">Избранные маршруты</span>
                  <span className="hero-chip">История поисков</span>
                  <span className="hero-chip">Личный кабинет</span>
                </div>
                <div className="account-promo-image">
                  <img src={visuals.rail} alt="Авторизация и профиль" />
                </div>
              </div>
            </div>
          </section>
        ) : (
          <>
            <section className="content-card account-card">
              <div className="account-hero">
                <div>
                  <p className="eyebrow">Личный кабинет</p>
                  <h2>{user.username}, ваш профиль подключен к поиску, истории и избранным маршрутам.</h2>
                  <p className="page-copy">
                    Теперь вы можете сохранять лучшие маршруты в избранное, быстро
                    возвращаться к ним и смотреть историю последних запросов.
                  </p>
                </div>
                <div className="account-hero-actions">
                  <Link to="/favorites" className="secondary-button">
                    Избранное
                  </Link>
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
                <div className="mini-card">
                  <span>Избранных маршрутов</span>
                  <strong>{user.favorites_count || 0}</strong>
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
