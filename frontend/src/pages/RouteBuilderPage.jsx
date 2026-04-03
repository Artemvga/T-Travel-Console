import { useEffect, useState } from "react";

import { visuals } from "../content/visuals";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Footer } from "../components/Footer";
import { Loader } from "../components/Loader";
import { Navbar } from "../components/Navbar";
import { RouteCard } from "../components/RouteCard";
import { RouteFilters } from "../components/RouteFilters";
import { RouteMap } from "../components/RouteMap";
import { SearchAutocomplete } from "../components/SearchAutocomplete";
import { buildRoute, getApiError, getCarriers } from "../services/api";

const initialFilters = {
  priority: "optimal",
  preferred_carriers: [],
  preferred_transport_types: [],
  direct_only: false,
  allow_transfers: true,
  max_transfers: 2,
};

const priorityLabels = {
  optimal: "Оптимальный",
  cheapest: "Дешевле",
  fastest: "Быстрее",
};

function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = `${today.getMonth() + 1}`.padStart(2, "0");
  const day = `${today.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function RouteBuilderPage() {
  const [fromCity, setFromCity] = useState(null);
  const [toCity, setToCity] = useState(null);
  const [viaCity, setViaCity] = useState(null);
  const [departureDate, setDepartureDate] = useState(getTodayDate);
  const [departureTime, setDepartureTime] = useState("00:00");
  const [filters, setFilters] = useState(initialFilters);
  const [carriers, setCarriers] = useState([]);
  const [loadingCarriers, setLoadingCarriers] = useState(true);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [result, setResult] = useState(null);
  const [showFilters, setShowFilters] = useState(true);

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
        const floor = viaCity ? 1 : 0;
        next.max_transfers = Math.max(floor, Math.min(5, Number(value) || 0));
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

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setError("");
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

  return (
    <div className="page-shell">
      <Navbar />

      <main className="page">
        <section className="content-card route-intro-card">
          <div className="route-intro-copy">
            <p className="eyebrow">Построение маршрута</p>
            <h1>Города сверху, настройки слева, карта и билеты сразу перед глазами.</h1>
            <p className="page-copy">
              Маршрут собирается из реальной билетной базы: учитываются время старта,
              приоритет поиска, компании, транзитный город и до пяти пересадок.
            </p>
            <div className="hero-chip-row">
              <span className="hero-chip">Компактные фильтры</span>
              <span className="hero-chip">Автобусы автоматически</span>
              <span className="hero-chip">Маршрут на карте Яндекса</span>
            </div>
          </div>
          <div className="route-intro-visual">
            <img src={visuals.hero} alt="Самолет на фоне города" />
          </div>
        </section>

        <div className={`route-layout ${showFilters ? "route-layout-open" : "route-layout-collapsed"}`}>
          <aside className={`route-sidebar ${showFilters ? "" : "route-sidebar-hidden"}`}>
            <div className="route-sidebar-header">
              <div>
                <p className="eyebrow">Параметры маршрута</p>
                <h2>Настройки поиска</h2>
              </div>
              <button
                type="button"
                className="secondary-button route-toggle-button"
                onClick={() => setShowFilters(false)}
              >
                Скрыть
              </button>
            </div>

            <section className="filter-card">
              <div className="filter-card-header">
                <p className="eyebrow">Дата</p>
                <p>Укажите момент, не раньше которого можно начать поездку.</p>
              </div>
              <div className="settings-grid">
                <label className="field-stack">
                  <span>Дата отправления</span>
                  <input
                    type="date"
                    value={departureDate}
                    onChange={(event) => setDepartureDate(event.target.value)}
                  />
                </label>
                <label className="field-stack">
                  <span>Время</span>
                  <input
                    type="time"
                    value={departureTime}
                    onChange={(event) => setDepartureTime(event.target.value)}
                  />
                </label>
              </div>
            </section>

            <RouteFilters
              carriers={carriers}
              values={filters}
              onChange={handleFilterChange}
              transitLocked={Boolean(viaCity)}
            />
          </aside>

          <section className="route-main">
            <form className="route-main-stack" onSubmit={handleSubmit}>
              <section className="content-card route-search-card">
                <div className="route-main-header">
                  <div>
                    <p className="eyebrow">Маршрут</p>
                    <h2>Соберите поездку и сразу смотрите билеты справа.</h2>
                  </div>
                  {!showFilters ? (
                    <button
                      type="button"
                      className="secondary-button route-toggle-button"
                      onClick={() => setShowFilters(true)}
                    >
                      Показать параметры
                    </button>
                  ) : null}
                </div>

                <div className="route-city-grid">
                  <SearchAutocomplete
                    label="Город отправления"
                    placeholder="Например, Нск или Новосибирск"
                    selectedCity={fromCity}
                    onSelect={setFromCity}
                    helper="Можно вводить название города или популярное сокращение."
                  />

                  <SearchAutocomplete
                    label="Город-транзит"
                    placeholder="Необязательно, например Новосибирск"
                    selectedCity={viaCity}
                    onSelect={handleTransitSelect}
                    helper="Если хотите поехать через конкретный узел, выберите его из подсказок."
                  />

                  <SearchAutocomplete
                    label="Город прибытия"
                    placeholder="Например, Томск или Владивосток"
                    selectedCity={toCity}
                    onSelect={setToCity}
                    helper="Подсказки покажут точный город из базы."
                  />
                </div>

                {formError ? (
                  <div className="inline-alert inline-alert-error">{formError}</div>
                ) : null}

                <div className="form-actions">
                  <button
                    type="submit"
                    className="primary-button"
                    disabled={loadingRoute || loadingCarriers}
                  >
                    {loadingRoute ? "Ищем билеты..." : "Показать билеты"}
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => {
                      setFromCity(null);
                      setToCity(null);
                      setViaCity(null);
                      setDepartureDate(getTodayDate());
                      setDepartureTime("00:00");
                      setFilters({ ...initialFilters });
                      setResult(null);
                      setError("");
                      setFormError("");
                    }}
                  >
                    Сбросить
                  </button>
                </div>
              </section>
            </form>

            {loadingRoute ? <Loader text="Подбираем билеты и собираем маршрут..." /> : null}

            {!loadingRoute && error ? (
              <ErrorState
                title="Поиск маршрута завершился ошибкой"
                message={error}
              />
            ) : null}

            {!loadingRoute && result?.status === "success" && result.best_route ? (
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
                      После {result.query.departure_time}
                    </span>
                    <span className="transport-tag">
                      {priorityLabels[result.query.priority] || result.query.priority}
                    </span>
                    <span className="transport-tag">
                      {result.best_route.segments.length} сегм.
                    </span>
                  </div>
                </div>

                <RouteMap
                  route={result.best_route}
                  title={`${result.query.from_city} → ${result.query.to_city}`}
                />

                <RouteCard
                  route={result.best_route}
                  title="Лучший маршрут"
                  highlight
                />

                {result.alternative_routes?.length ? (
                  <div className="results-stack">
                    <p className="eyebrow">Альтернативы</p>
                    {result.alternative_routes.map((route, index) => (
                      <RouteCard
                        key={`${route.total_price}-${route.total_duration_minutes}-${index}`}
                        route={route}
                        title={`Альтернатива ${index + 1}`}
                      />
                    ))}
                  </div>
                ) : null}
              </section>
            ) : null}

            {!loadingRoute && result?.status === "empty" ? (
              <EmptyState
                title="Маршруты не найдены"
                message={result.message}
              />
            ) : null}

            {!loadingRoute && !result && !error ? (
              <EmptyState
                title="Маршрут пока не построен"
                message="Выберите города сверху, настройте фильтры слева и получите карту с билетами ниже."
              />
            ) : null}
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
