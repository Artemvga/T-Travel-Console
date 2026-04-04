import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Footer } from "../components/Footer";
import { Loader } from "../components/Loader";
import { Navbar } from "../components/Navbar";
import { RouteCard } from "../components/RouteCard";
import { RouteMap } from "../components/RouteMap";
import { useAuth } from "../context/AuthContext";
import { getApiError, getFavoriteRoutes, removeFavoriteRoute } from "../services/api";

function favoriteLabel(item) {
  const fromCity = item.query?.from_city || item.from_city?.name || "Маршрут";
  const toCity = item.query?.to_city || item.to_city?.name || "";
  return toCity ? `${fromCity} → ${toCity}` : fromCity;
}

export function FavoritesPage() {
  const { ready, isAuthenticated, refreshProfile } = useAuth();
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    if (!ready) {
      return;
    }

    if (!isAuthenticated) {
      setLoading(false);
      setFavorites([]);
      setActiveId(null);
      return;
    }

    let cancelled = false;

    const loadFavorites = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await getFavoriteRoutes();
        if (!cancelled) {
          setFavorites(data);
          setActiveId(data[0]?.id || null);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(getApiError(requestError, "Не удалось загрузить избранные маршруты."));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadFavorites();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, ready]);

  const activeFavorite = useMemo(
    () => favorites.find((item) => item.id === activeId) || favorites[0] || null,
    [activeId, favorites],
  );

  const handleRemove = async (favoriteId) => {
    try {
      await removeFavoriteRoute(favoriteId);
      const nextFavorites = favorites.filter((item) => item.id !== favoriteId);
      setFavorites(nextFavorites);
      if (activeId === favoriteId) {
        setActiveId(nextFavorites[0]?.id || null);
      }
      refreshProfile().catch(() => {});
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось удалить маршрут из избранного."));
    }
  };

  if (!ready) {
    return (
      <div className="page-shell">
        <Navbar />
        <main className="page">
          <Loader text="Подключаем избранное..." />
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
          <section className="content-card favorites-gate-card">
            <p className="eyebrow">Избранное</p>
            <h1>Войдите в аккаунт, чтобы сохранять маршруты и открывать их в один клик.</h1>
            <p className="page-copy">
              После авторизации можно добавлять найденные маршруты в избранное,
              быстро возвращаться к ним и сразу смотреть путь на карте.
            </p>
            <div className="hero-actions">
              <Link to="/account" className="primary-button">
                Войти в аккаунт
              </Link>
              <Link to="/routes" className="secondary-button">
                Перейти к поиску
              </Link>
            </div>
          </section>
        ) : null}

        {isAuthenticated && loading ? <Loader text="Загружаем избранные маршруты..." /> : null}

        {isAuthenticated && !loading && error ? (
          <ErrorState title="Не удалось открыть избранное" message={error} />
        ) : null}

        {isAuthenticated && !loading && !error && !favorites.length ? (
          <EmptyState
            title="Избранное пока пустое"
            message="Сохраните маршрут со страницы построения, и он появится здесь."
          />
        ) : null}

        {isAuthenticated && !loading && !error && activeFavorite ? (
          <section className="favorites-layout">
            <section className="content-card favorites-preview-card">
              <div className="results-heading">
                <div>
                  <p className="eyebrow">Избранный маршрут</p>
                  <h2>{favoriteLabel(activeFavorite)}</h2>
                  <p>
                    Сохранено {new Date(activeFavorite.created_at).toLocaleString("ru-RU")}
                  </p>
                </div>
                <div className="results-heading-meta">
                  <span className="transport-tag">
                    {activeFavorite.query?.priority === "fastest"
                      ? "Быстрее"
                      : activeFavorite.query?.priority === "cheapest"
                        ? "Дешевле"
                        : "Оптимально"}
                  </span>
                  {activeFavorite.query?.via_city ? (
                    <span className="transport-tag">Через {activeFavorite.query.via_city}</span>
                  ) : null}
                </div>
              </div>

              <RouteMap route={activeFavorite.route} title={favoriteLabel(activeFavorite)} />
              <RouteCard route={activeFavorite.route} title={activeFavorite.route_title || "Избранное"} highlight />
            </section>

            <aside className="content-card favorites-list-card">
              <div className="section-head">
                <div>
                  <p className="eyebrow">Список</p>
                  <h2>Сохраненные маршруты</h2>
                </div>
              </div>

              <div className="favorites-list">
                {favorites.map((favorite) => (
                  <article
                    key={favorite.id}
                    className={`favorite-list-item ${
                      activeFavorite.id === favorite.id ? "favorite-list-item-active" : ""
                    }`}
                  >
                    <button
                      type="button"
                      className="favorite-list-button"
                      onClick={() => setActiveId(favorite.id)}
                    >
                      <strong>{favorite.route_title || favoriteLabel(favorite)}</strong>
                      <span>{favoriteLabel(favorite)}</span>
                    </button>
                    <button
                      type="button"
                      className="secondary-button favorite-remove-button"
                      onClick={() => handleRemove(favorite.id)}
                    >
                      Удалить
                    </button>
                  </article>
                ))}
              </div>
            </aside>
          </section>
        ) : null}
      </main>

      <Footer />
    </div>
  );
}
