import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Footer } from "../components/Footer";
import { Hero } from "../components/Hero";
import { Navbar } from "../components/Navbar";
import { visuals } from "../content/visuals";
import { getStats } from "../services/api";
import { formatCompactNumber } from "../utils/format";

const transportMarks = {
  plane: "✈",
  train: "ЖД",
  bus: "BUS",
  electric_train: "ЭЛ",
};

const transportVisuals = {
  plane: visuals.hero,
  train: visuals.rail,
};

function buildCategorySections(stats) {
  if (stats?.transport_sections?.length) {
    return stats.transport_sections;
  }

  return [
    {
      transport_type: "plane",
      label: "Самолеты",
      tickets_count: 770400,
      popular_directions: [
        { from_city: "Новосибирск", to_city: "Москва", tickets_count: 480 },
        { from_city: "Новосибирск", to_city: "Владивосток", tickets_count: 360 },
      ],
    },
    {
      transport_type: "train",
      label: "Поезда",
      tickets_count: 1051200,
      popular_directions: [
        { from_city: "Новосибирск", to_city: "Томск", tickets_count: 720 },
        { from_city: "Москва", to_city: "Санкт-Петербург", tickets_count: 720 },
      ],
    },
    {
      transport_type: "bus",
      label: "Автобусы",
      tickets_count: 3247200,
      popular_directions: [
        { from_city: "Новосибирск", to_city: "Томск", tickets_count: 720 },
        { from_city: "Томск", to_city: "Кемерово", tickets_count: 600 },
      ],
    },
    {
      transport_type: "electric_train",
      label: "Электрички",
      tickets_count: 77760,
      popular_directions: [
        { from_city: "Москва", to_city: "Тула", tickets_count: 240 },
        { from_city: "Санкт-Петербург", to_city: "Великий Новгород", tickets_count: 240 },
      ],
    },
  ];
}

export function HomePage() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let isCancelled = false;

    const loadStats = async () => {
      try {
        const data = await getStats();
        if (!isCancelled) {
          setStats(data);
        }
      } catch {
        if (!isCancelled) {
          setStats(null);
        }
      }
    };

    loadStats();
    return () => {
      isCancelled = true;
    };
  }, []);

  const sections = buildCategorySections(stats);

  return (
    <div className="page-shell">
      <Navbar />

      <main className="page">
        <Hero stats={stats} />

        <section className="wide-card feature-band">
          <article className="feature-band-card feature-band-card-dark">
            <span className="eyebrow">Что уже умеет сайт</span>
            <h2>Поиск маршрута, информация о городе, карта и личный кабинет собраны в один продукт.</h2>
            <p>
              Мы ушли от консольного сценария к цельному веб-интерфейсу, где
              маршрут, ограничения, карта и найденные билеты находятся в одном
              потоке.
            </p>
          </article>
          <article className="feature-band-card">
            <span className="eyebrow">Следующий шаг</span>
            <strong>Открыть построение маршрута и попробовать поиск с транзитом.</strong>
            <Link to="/routes" className="secondary-button">
              Перейти к маршрутам
            </Link>
          </article>
          <article className="feature-band-image">
            <img src={visuals.rail} alt="Современный поезд" />
          </article>
        </section>

        <section className="wide-card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Сводка</p>
              <h2>Билеты по категориям, популярные направления и активные транспортные витрины.</h2>
            </div>
          </div>

          <div className="summary-category-grid">
            {sections.map((section) => (
              <article key={section.transport_type} className="summary-category-card">
                {transportVisuals[section.transport_type] ? (
                  <div className="summary-category-image">
                    <img src={transportVisuals[section.transport_type]} alt={section.label} />
                  </div>
                ) : null}
                <div className="summary-category-top">
                  <span className="transport-category-mark">
                    {transportMarks[section.transport_type] || "TP"}
                  </span>
                  <div>
                    <span className="summary-category-label">{section.label}</span>
                    <strong>{formatCompactNumber(section.tickets_count)} билетов</strong>
                  </div>
                </div>

                <div className="summary-category-body">
                  <span className="summary-category-subtitle">Популярные направления</span>
                  <ul className="summary-direction-list">
                    {section.popular_directions?.slice(0, 3).map((direction) => (
                      <li
                        key={`${section.transport_type}-${direction.from_city}-${direction.to_city}`}
                      >
                        <span>
                          {direction.from_city} → {direction.to_city}
                        </span>
                        <strong>{formatCompactNumber(direction.tickets_count)}</strong>
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
