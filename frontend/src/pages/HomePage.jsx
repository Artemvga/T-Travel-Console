import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Footer } from "../components/Footer";
import { Hero } from "../components/Hero";
import { Navbar } from "../components/Navbar";
import { TransportGlyph } from "../components/TransportGlyph";
import { visuals } from "../content/visuals";
import { getStats } from "../services/api";
import { formatCompactNumber } from "../utils/format";

const transportMarks = {
  plane: { className: "transport-category-mark-plane" },
  train: { className: "transport-category-mark-train" },
  bus: { className: "transport-category-mark-bus" },
  electric_train: { className: "transport-category-mark-electric" },
};

function getPopularDirections(section) {
  const directions = section.popular_directions?.slice(0, 3) || [];

  if (directions.length) {
    const preparedDirections = directions.map((direction) => ({
      key: `${section.transport_type}-${direction.from_city}-${direction.to_city}`,
      label: `${direction.from_city} → ${direction.to_city}`,
      value: formatCompactNumber(direction.tickets_count),
      empty: false,
    }));

    while (preparedDirections.length < 3) {
      preparedDirections.push({
        key: `${section.transport_type}-placeholder-${preparedDirections.length}`,
        label: "Новые направления будут показаны здесь",
        value: "—",
        empty: true,
      });
    }

    return preparedDirections;
  }

  return [
    {
      key: `${section.transport_type}-empty`,
      label: "Пока нет активных направлений",
      value: "—",
      empty: true,
    },
  ];
}

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
          <article className="feature-band-card feature-band-card-dark feature-band-card-evening">
            <span className="eyebrow">Что уже умеет сайт</span>
            <h2>Маршруты, карта, информация о городе и личный кабинет работают как единый сервис.</h2>
            <p>
              Вместо консольного сценария теперь есть цельный веб-интерфейс:
              поиск, фильтры, карта и найденные билеты собраны в одном потоке.
            </p>
          </article>
          <article className="feature-band-card feature-band-card-facts">
            <span className="eyebrow">Интересные факты</span>
            <strong>Сразу показываем маршрут на карте и даем быстро сравнить весь путь.</strong>
            <ul className="fact-list">
              <li>Маршрут отображается на Яндекс Карте по каждому сегменту.</li>
              <li>Можно увидеть, сколько времени занимает каждый вид транспорта.</li>
              <li>После входа маршрут сохраняется в избранное в один клик.</li>
            </ul>
            <Link to="/routes" className="secondary-button">
              Перейти к маршрутам
            </Link>
          </article>
          <article className="feature-band-image">
            <img src={visuals.city} alt="Городской пейзаж" />
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
              <article
                key={section.transport_type}
                className={`summary-category-card summary-category-card-${section.transport_type}`}
              >
                <div className="summary-category-top">
                  <span
                    className={`transport-category-mark ${
                      transportMarks[section.transport_type]?.className || ""
                    }`}
                  >
                    <TransportGlyph
                      type={section.transport_type}
                      className="transport-category-glyph"
                    />
                  </span>
                  <div>
                    <span className="summary-category-label">{section.label}</span>
                    <strong>{formatCompactNumber(section.tickets_count)} билетов</strong>
                  </div>
                </div>

                <div className="summary-category-body">
                  <span className="summary-category-subtitle">Популярные направления</span>
                  <ul className="summary-direction-list">
                    {getPopularDirections(section).map((direction) => (
                      <li
                        key={direction.key}
                        className={direction.empty ? "summary-direction-empty" : ""}
                      >
                        <span>{direction.label}</span>
                        <strong>{direction.value}</strong>
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
