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
        <p className="eyebrow">Т-Путешествия</p>
        <h1>Маршруты по России с картой, билетами и умной логикой пересадок.</h1>
        <p>
          Проверьте город, сравните транспортные узлы и соберите маршрут по
          России с билетами, временем в пути, обязательным транзитным городом
          и до пяти пересадок, если это нужно вашему сценарию.
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
          <span>Маршрутный сценарий</span>
          <strong>Москва → Новосибирск → Владивосток</strong>
          <p>Один интерфейс для выбора параметров, карты и итоговых билетов.</p>
        </article>
        <article className="hero-floating-card hero-floating-card-dark">
          <span>Приоритеты</span>
          <strong>Быстрее, дешевле или оптимально</strong>
        </article>
      </div>
    </section>
  );
}
