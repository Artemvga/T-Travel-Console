import { Link } from "react-router-dom";

import { visuals } from "../content/visuals";
import { formatCompactNumber } from "../utils/format";

function buildStats(stats) {
  if (!stats) {
    return [
      { label: "Городов", value: "1 117" },
      { label: "Билетов", value: "миллионы" },
      { label: "Транспорт", value: "4 вида" },
    ];
  }

  return [
    {
      label: "Городов",
      value: new Intl.NumberFormat("ru-RU").format(stats.cities_count),
    },
    {
      label: "Билетов",
      value: formatCompactNumber(stats.tickets_count),
    },
    {
      label: "Активных маршрутов",
      value: formatCompactNumber(stats.active_tickets_count),
    },
  ];
}

export function Hero({ stats }) {
  const statCards = buildStats(stats);

  return (
    <section className="hero-section hero-section-compact">
      <div className="hero-content">
        <h1>Карта, билеты и маршрут по России в одном окне.</h1>
        <p>
          Проверьте город, сравните транспортные узлы и соберите маршрут по
          России с понятной логикой пересадок, временем в пути, выбором приоритета
          и отображением пути на Яндекс Карте.
        </p>

        <div className="hero-chip-row">
          <span className="hero-chip">До 5 пересадок</span>
          <span className="hero-chip">Транзитный город</span>
          <span className="hero-chip">Карта Яндекса</span>
        </div>

        <div className="hero-actions">
          <Link to="/routes" className="primary-button">
            Найти маршрут
          </Link>
          <Link to="/cities" className="secondary-button">
            Открыть город
          </Link>
        </div>

        <div className="hero-stat-strip">
          {statCards.map((item) => (
            <article key={item.label} className="hero-stat-card">
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </article>
          ))}
        </div>
      </div>

      <div className="hero-visual">
        <article className="hero-image-card">
          <img src={visuals.hero} alt="Полет над городом" />
        </article>
        <article className="hero-floating-card">
          <span>Как это работает</span>
          <strong>Выберите города, настройте дату и сразу получите билеты с картой.</strong>
          <p>Маршрут можно сразу открыть, сравнить и сохранить в избранное после входа.</p>
        </article>
        <article className="hero-floating-card hero-floating-card-dark">
          <span>Приоритеты</span>
          <strong>Быстрее • Дешевле • Оптимально</strong>
        </article>
      </div>
    </section>
  );
}
