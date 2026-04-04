import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Footer } from "../components/Footer";
import { Loader } from "../components/Loader";
import { Navbar } from "../components/Navbar";
import { RouteCard } from "../components/RouteCard";
import { RouteFilters } from "../components/RouteFilters";
import { RouteMap } from "../components/RouteMap";
import { SearchAutocomplete } from "../components/SearchAutocomplete";
import { useAuth } from "../context/AuthContext";
import {
  buildRoute,
  getApiError,
  getCarriers,
  getGenerationStatus,
  getFavoriteRoutes,
  saveFavoriteRoute,
} from "../services/api";
import { formatDuration } from "../utils/format";

const initialFilters = {
  preferred_carriers: [],
  preferred_transport_types: [],
  direct_only: false,
  allow_transfers: true,
  max_transfers: 3,
};

const priorityOptions = [
  { value: "optimal", label: "Оптимально", note: "Баланс по цене и времени" },
  { value: "cheapest", label: "Дешевле", note: "Сначала минимальная цена" },
  { value: "fastest", label: "Быстрее", note: "Сначала минимальное время" },
];

const priorityLabels = {
  optimal: "Оптимально",
  cheapest: "Дешевле",
  fastest: "Быстрее",
};

const transportLabels = {
  plane: "Самолет",
  train: "Поезд",
  bus: "Автобус",
  electric_train: "Электричка",
};

function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = `${today.getMonth() + 1}`.padStart(2, "0");
  const day = `${today.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getSuggestedRouteDate(minDepartureDate) {
  const today = getTodayDate();
  if (!minDepartureDate) {
    return today;
  }
  return today > minDepartureDate ? today : minDepartureDate;
}

function buildRouteKey(route) {
  return route?.segments?.map((segment) => segment.external_id).join("|") || "";
}

function summarizeRoute(route) {
  const transportTypes = [...new Set((route?.segments || []).map((segment) => transportLabels[segment.transport_type]))];
  return {
    cities: route?.waypoints?.length || 0,
    segments: route?.segments?.length || 0,
    transport: transportTypes.join(" • ") || "Смешанный маршрут",
  };
}

function segmentBadgeLabel(count) {
  if (count === 1) {
    return "1 сегмент";
  }
  if (count >= 2 && count <= 4) {
    return `${count} сегмента`;
  }
  return `${count} сегментов`;
}

export function RouteBuilderPage() {
  const { isAuthenticated, refreshProfile } = useAuth();
  const mapRef = useRef(null);
  const priorityDropdownRef = useRef(null);
  const [fromCity, setFromCity] = useState(null);
  const [toCity, setToCity] = useState(null);
  const [viaCity, setViaCity] = useState(null);
  const [departureDate, setDepartureDate] = useState(getTodayDate);
  const [departureTime, setDepartureTime] = useState("00:00");
  const [priority, setPriority] = useState("optimal");
  const [priorityOpen, setPriorityOpen] = useState(false);
  const [filters, setFilters] = useState(initialFilters);
  const [carriers, setCarriers] = useState([]);
  const [loadingCarriers, setLoadingCarriers] = useState(true);
  const [generationStatus, setGenerationStatus] = useState(null);
  const [loadingGenerationStatus, setLoadingGenerationStatus] = useState(true);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [favoriteMessage, setFavoriteMessage] = useState("");
  const [savingFavoriteKey, setSavingFavoriteKey] = useState("");
  const [savedRouteKeys, setSavedRouteKeys] = useState([]);
  const [result, setResult] = useState(null);
  const [activeRouteKey, setActiveRouteKey] = useState("");

  useEffect(() => {
    const loadCarriers = async () => {
      setLoadingCarriers(true);
      try {
        const data = await getCarriers();
        setCarriers(data);
      } catch (requestError) {
        setError(getApiError(requestError, "Не удалось загрузить список перевозчиков."));
      } finally {
        setLoadingCarriers(false);
      }
    };

    loadCarriers();
  }, []);

  useEffect(() => {
    const loadGenerationStatus = async () => {
      setLoadingGenerationStatus(true);
      try {
        const data = await getGenerationStatus();
        setGenerationStatus(data);
      } catch (requestError) {
        setError(getApiError(requestError, "Не удалось загрузить состояние билетной базы."));
      } finally {
        setLoadingGenerationStatus(false);
      }
    };

    loadGenerationStatus();
  }, []);

  useEffect(() => {
    const minDepartureDate = generationStatus?.min_departure_date;
    if (!minDepartureDate) {
      return;
    }
    setDepartureDate((current) => {
      if (!current || current < minDepartureDate) {
        return getSuggestedRouteDate(minDepartureDate);
      }
      return current;
    });
  }, [generationStatus?.min_departure_date]);

  useEffect(() => {
    if (!isAuthenticated) {
      setSavedRouteKeys([]);
      return;
    }

    let cancelled = false;

    const loadFavorites = async () => {
      try {
        const favorites = await getFavoriteRoutes();
        if (!cancelled) {
          setSavedRouteKeys(
            favorites
              .map((item) => buildRouteKey(item.route))
              .filter(Boolean),
          );
        }
      } catch {
        if (!cancelled) {
          setSavedRouteKeys([]);
        }
      }
    };

    loadFavorites();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!priorityDropdownRef.current?.contains(event.target)) {
        setPriorityOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const routes = useMemo(() => {
    if (result?.status !== "success") {
      return [];
    }
    return [result.best_route, ...(result.alternative_routes || [])].filter(Boolean);
  }, [result]);

  useEffect(() => {
    if (routes.length) {
      setActiveRouteKey(buildRouteKey(routes[0]));
    } else {
      setActiveRouteKey("");
    }
  }, [routes]);

  const activeRoute = useMemo(
    () => routes.find((route) => buildRouteKey(route) === activeRouteKey) || routes[0] || null,
    [activeRouteKey, routes],
  );
  const activeRouteSummary = summarizeRoute(activeRoute);

  const handleFilterChange = (field, value) => {
    setFilters((current) => {
      const next = {
        ...current,
        [field]: value,
      };

      if (viaCity) {
        if (field === "direct_only" && value) {
          next.direct_only = false;
        }
        if (field === "allow_transfers" && !value) {
          next.allow_transfers = true;
        }
        if (field === "max_transfers" && Number(value) < 1) {
          next.max_transfers = 1;
        }
      }

      if (field === "max_transfers") {
        const floor = viaCity ? 1 : 1;
        next.max_transfers = Math.max(floor, Math.min(5, Number(value) || 1));
      }

      return next;
    });
  };

  const handleTransitSelect = (city) => {
    setViaCity(city);
    if (city) {
      setFilters((current) => ({
        ...current,
        direct_only: false,
        allow_transfers: true,
        max_transfers: Math.max(1, current.max_transfers),
      }));
    }
  };

  const resetForm = () => {
    setFromCity(null);
    setToCity(null);
    setViaCity(null);
    setDepartureDate(getSuggestedRouteDate(generationStatus?.min_departure_date));
    setDepartureTime("00:00");
    setPriority("optimal");
    setFilters({ ...initialFilters });
    setResult(null);
    setError("");
    setFormError("");
    setFavoriteMessage("");
    setSavedRouteKeys([]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setError("");
    setFavoriteMessage("");
    setResult(null);

    if (!fromCity || !toCity) {
      setFormError("Выберите города отправления и прибытия из подсказок.");
      return;
    }

    if (fromCity.slug === toCity.slug) {
      setFormError("Города отправления и прибытия должны различаться.");
      return;
    }

    if (!departureDate) {
      setFormError("Укажите дату отправления.");
      return;
    }

    if (!generationStatus?.dataset_ready) {
      setFormError("Билетная база еще не собрана. Сначала выполните локальную генерацию и импорт билетов.");
      return;
    }

    if (viaCity && (viaCity.slug === fromCity.slug || viaCity.slug === toCity.slug)) {
      setFormError("Транзитный город должен отличаться от точки отправления и прибытия.");
      return;
    }

    setLoadingRoute(true);
    try {
      const data = await buildRoute({
        from_city: fromCity.slug,
        to_city: toCity.slug,
        via_city: viaCity?.slug || "",
        departure_date: departureDate,
        departure_time: departureTime,
        priority,
        ...filters,
      });
      setResult(data);
    } catch (requestError) {
      setResult(null);
      setError(getApiError(requestError, "Не удалось построить маршрут."));
    } finally {
      setLoadingRoute(false);
    }
  };

  const handleShowRouteOnMap = (route) => {
    setActiveRouteKey(buildRouteKey(route));
    mapRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleSaveFavorite = async (route, title) => {
    if (!isAuthenticated || !result?.query) {
      setFavoriteMessage("Сохранять маршруты в избранное можно после входа в аккаунт.");
      return;
    }

    const routeKey = buildRouteKey(route);
    setSavingFavoriteKey(routeKey);
    setFavoriteMessage("");

    try {
      await saveFavoriteRoute({
        route_title: title,
        query: result.query,
        route_data: route,
      });
      setSavedRouteKeys((current) => [...new Set([...current, routeKey])]);
      setFavoriteMessage("Маршрут сохранен в избранное.");
      refreshProfile().catch(() => {});
    } catch (requestError) {
      setFavoriteMessage(getApiError(requestError, "Не удалось сохранить маршрут в избранное."));
    } finally {
      setSavingFavoriteKey("");
    }
  };

  return (
    <div className="page-shell">
      <Navbar />

      <main className="page">
        <section className="route-builder-shell">
          <aside className="content-card route-settings-board">
            <div className="section-head section-head-compact">
              <div>
                <p className="eyebrow">Настройки поиска</p>
                <h2>Фильтры и режим маршрута</h2>
              </div>
            </div>
            <RouteFilters
              carriers={carriers}
              values={filters}
              onChange={handleFilterChange}
              transitLocked={Boolean(viaCity)}
            />
          </aside>

          <section className="content-card route-search-card route-search-card-reworked">
            <div className="route-main-header route-main-header-compact">
              <div>
                <p className="eyebrow">Построение маршрута</p>
                <h1>Соберите маршрут и сразу откройте его на карте.</h1>
                <p className="page-copy route-search-lead">
                  Города, дата, время и приоритет находятся в главной панели
                  маршрута, а транспортные фильтры и режим поиска собраны в
                  компактной левой колонке.
                </p>
              </div>
            </div>

            <form className="route-form-layout" onSubmit={handleSubmit}>
              <div className="route-city-grid route-city-grid-tight">
                <SearchAutocomplete
                  label="Город отправления"
                  placeholder="Например, Нск или Новосибирск"
                  selectedCity={fromCity}
                  onSelect={setFromCity}
                  helper="Введите название или сокращение."
                />

                <SearchAutocomplete
                  label="Город-транзит"
                  placeholder="Необязательно, например Екатеринбург"
                  selectedCity={viaCity}
                  onSelect={handleTransitSelect}
                  helper="Необязательная точка маршрута."
                />

                <SearchAutocomplete
                  label="Город прибытия"
                  placeholder="Например, Томск или Владивосток"
                  selectedCity={toCity}
                  onSelect={setToCity}
                  helper="Подсказки покажут точный город."
                />
              </div>

              <div className="route-meta-grid">
                <label className="field-stack route-inline-field">
                  <span>Дата отправления</span>
                  <input
                    type="date"
                    min={generationStatus?.min_departure_date || getTodayDate()}
                    value={departureDate}
                    onChange={(event) => setDepartureDate(event.target.value)}
                  />
                </label>

                <label className="field-stack route-inline-field">
                  <span>Время</span>
                  <input
                    type="time"
                    value={departureTime}
                    onChange={(event) => setDepartureTime(event.target.value)}
                  />
                </label>

                <div className="field-stack route-inline-field" ref={priorityDropdownRef}>
                  <span>Приоритет</span>
                  <div className={`priority-select ${priorityOpen ? "priority-select-open" : ""}`}>
                    <button
                      type="button"
                      className="priority-select-trigger"
                      onClick={() => setPriorityOpen((current) => !current)}
                    >
                      <strong>{priorityLabels[priority]}</strong>
                      <small>
                        {priorityOptions.find((item) => item.value === priority)?.note}
                      </small>
                    </button>
                    {priorityOpen ? (
                      <div className="priority-select-menu">
                        {priorityOptions.map((option) => (
                          <button
                            key={option.value}
                            type="button"
                            className={`priority-option ${
                              priority === option.value ? "priority-option-active" : ""
                            }`}
                            onClick={() => {
                              setPriority(option.value);
                              setPriorityOpen(false);
                            }}
                          >
                            <strong>{option.label}</strong>
                            <small>{option.note}</small>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>

              {formError ? (
                <div className="inline-alert inline-alert-error" role="alert">{formError}</div>
              ) : null}
              {generationStatus ? (
                <div className="inline-alert" role="status">
                  {generationStatus.dataset_ready
                    ? `База готова: ${generationStatus.active_tickets_count} активных билетов, окно дат ${generationStatus.min_departure_date} - ${generationStatus.max_departure_date}.`
                    : "База билетов пока не собрана. Поиск станет доступен после локальной генерации и импорта."}
                </div>
              ) : null}
              {favoriteMessage ? (
                <div
                  role="alert"
                  className={`inline-alert ${
                    favoriteMessage.toLowerCase().includes("не удалось") ||
                    favoriteMessage.toLowerCase().includes("можно после входа")
                      ? "inline-alert-error"
                      : ""
                  }`}
                >
                  {favoriteMessage}
                </div>
              ) : null}

              <div className="route-form-actions">
                <button
                  type="submit"
                  className="primary-button"
                  disabled={
                    loadingRoute
                    || loadingCarriers
                    || loadingGenerationStatus
                    || !generationStatus?.dataset_ready
                  }
                >
                  {loadingRoute ? "Ищем билеты..." : "Показать билеты"}
                </button>
                <button type="button" className="secondary-button" onClick={resetForm}>
                  Сбросить
                </button>
                {!isAuthenticated ? (
                  <Link to="/account" className="secondary-button route-inline-link">
                    Войти для избранного
                  </Link>
                ) : null}
              </div>
            </form>
          </section>
        </section>

        {loadingRoute || loadingGenerationStatus ? (
          <Loader
            text={
              loadingGenerationStatus
                ? "Проверяем состояние билетной базы..."
                : "Подбираем билеты и собираем маршрут..."
            }
          />
        ) : null}

        {!loadingRoute && error ? (
          <ErrorState title="Поиск маршрута завершился ошибкой" message={error} />
        ) : null}

        {!loadingRoute && result?.status === "success" && activeRoute ? (
          <section className="results-stack">
            <div className="results-heading">
              <div>
                <p className="eyebrow">Лучший результат</p>
                <h2>
                  {result.query.from_city} → {result.query.to_city}
                </h2>
                <p>{result.message}</p>
              </div>
              <div className="results-heading-meta">
                {result.query.via_city ? (
                  <span className="transport-tag">Через {result.query.via_city}</span>
                ) : null}
                <span className="transport-tag">
                  {priorityLabels[result.query.priority] || result.query.priority}
                </span>
                <span className="transport-tag">
                  {segmentBadgeLabel(activeRoute.segments.length)}
                </span>
              </div>
            </div>

            <div className="route-facts-grid">
              <article className="mini-card">
                <span>Города на пути</span>
                <strong>{activeRouteSummary.cities}</strong>
              </article>
              <article className="mini-card">
                <span>Транспорт</span>
                <strong>{activeRouteSummary.transport}</strong>
              </article>
              <article className="mini-card">
                <span>Общее время</span>
                <strong>{formatDuration(activeRoute.total_duration_minutes)}</strong>
              </article>
              <article className="mini-card">
                <span>Сегменты</span>
                <strong>{activeRouteSummary.segments}</strong>
              </article>
            </div>

            <div ref={mapRef}>
              <RouteMap
                route={activeRoute}
                title={`${activeRoute.waypoints?.[0]?.name || result.query.from_city} → ${
                  activeRoute.waypoints?.[activeRoute.waypoints?.length - 1]?.name || result.query.to_city
                }`}
              />
            </div>

            <div className="results-route-grid">
              {routes.map((route, index) => {
                const routeTitle =
                  index === 0
                    ? "Лучший маршрут"
                    : `Другой подходящий вариант ${index}`;
                const routeKey = buildRouteKey(route);
                const isSaved = savedRouteKeys.includes(routeKey);
                const isActive = activeRouteKey === routeKey;

                return (
                  <RouteCard
                    key={routeKey || `${route.total_price}-${index}`}
                    route={route}
                    title={routeTitle}
                    highlight={index === 0}
                    actions={
                      <>
                        <button
                          type="button"
                          className={`secondary-button ${isActive ? "mode-active" : ""}`}
                          onClick={() => handleShowRouteOnMap(route)}
                        >
                          Показать путь на карте
                        </button>
                        {isAuthenticated ? (
                          <button
                            type="button"
                            className="primary-button"
                            disabled={Boolean(savingFavoriteKey) && savingFavoriteKey === routeKey}
                            onClick={() => handleSaveFavorite(route, routeTitle)}
                          >
                            {isSaved
                              ? "Сохранено"
                              : savingFavoriteKey === routeKey
                                ? "Сохраняем..."
                                : "Добавить в избранное"}
                          </button>
                        ) : (
                          <Link to="/account" className="secondary-button">
                            Войти для избранного
                          </Link>
                        )}
                      </>
                    }
                  />
                );
              })}
            </div>
          </section>
        ) : null}

        {!loadingRoute && !loadingGenerationStatus && generationStatus && !generationStatus.dataset_ready ? (
          <EmptyState
            title="База билетов еще не готова"
            message="Импорт городов и перевозчиков уже может работать, но для поиска маршрутов нужно сначала собрать локальную билетную базу."
          />
        ) : null}

        {!loadingRoute && result?.status === "empty" ? (
          <EmptyState
            title={
              result.reason === "dataset_not_seeded"
                ? "База билетов еще не собрана"
                : "Маршруты не найдены"
            }
            message={result.message}
          />
        ) : null}
      </main>

      <Footer />
    </div>
  );
}
