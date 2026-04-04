import { formatCompactNumber } from "../utils/format";
import { TransportGlyph } from "./TransportGlyph";

const transportLabels = {
  bus: "Автобус",
  train: "Поезд",
  plane: "Самолет",
  electric_train: "Электричка",
};

function HubCard({ type, label, active }) {
  return (
    <article className={`hub-card ${active ? "hub-card-active" : "hub-card-muted"}`}>
      <span className="hub-card-icon hub-card-icon-glyph">
        <TransportGlyph type={type} />
      </span>
      <div>
        <strong>{label}</strong>
        <p>{active ? "Есть в городской витрине" : "Пока нет подтверждения"}</p>
      </div>
    </article>
  );
}

export function CityInfoCard({ city, embedded = false }) {
  const hubCards = [
    { type: "bus", label: "Автобусная станция", active: city.has_bus_station },
    {
      type: "plane",
      label: city.has_international_airport ? "Международный аэропорт" : "Аэропорт",
      active: city.has_airport,
    },
    { type: "train", label: "Ж/д станция", active: city.has_train_station },
    {
      type: "electric_train",
      label: "Электрички",
      active: city.has_commuter_station,
    },
  ];

  const transportMixRows = city.tickets_by_transport?.length
    ? city.tickets_by_transport.map((item) => ({
        label: transportLabels[item.transport_type] || item.transport_type,
        value: item.tickets_count ? "Есть в базе" : "Нет данных",
      }))
    : [];
  const popularRoutes = city.popular_destinations?.length
    ? city.popular_destinations.map((item) => item.name)
    : [];
  const Wrapper = embedded ? "div" : "section";

  return (
    <Wrapper className={embedded ? "city-info-card-live city-info-card-live-embedded" : "info-card city-info-card-live"}>
      <div className="city-info-hero">
        <div className="info-card-header">
          <div>
            <p className="eyebrow">Профиль города</p>
            <h2>{city.name}</h2>
            <p className="city-card-copy">
            {city.region}
            {city.population
                ? ` • ${new Intl.NumberFormat("ru-RU").format(city.population)} жителей`
                : ""}
            </p>
            <p className="city-card-copy">
              Видно ключевые транспортные узлы, состояние витрины билетов и
              наиболее частые направления для этого города.
            </p>
          </div>
        </div>
      </div>

      <div className="city-live-grid">
        <article className="city-spotlight">
          <span>Билетов с участием города</span>
          <strong>{formatCompactNumber(city.active_tickets_count || 0)}</strong>
          <p>Чем больше число, тем активнее город в текущей витрине.</p>
        </article>

        <article className="city-spotlight">
          <span>Доступных направлений</span>
          <strong>{formatCompactNumber(city.available_directions_count || 0)}</strong>
          <p>Уникальные направления, в которые можно уехать или прилететь.</p>
        </article>

        <article className="city-spotlight">
          <span>Активных перевозчиков</span>
          <strong>{formatCompactNumber(city.city_energy || 0)}</strong>
          <p>Сколько разных перевозчиков участвуют в жизни этого города.</p>
        </article>
      </div>

      <div className="hub-grid">
        {hubCards.map((item) => (
          <HubCard
            key={item.label}
            type={item.type}
            label={item.label}
            active={item.active}
          />
        ))}
      </div>

      <div className="city-table-grid">
        <div className="mini-card city-table-card">
          <span>Транспортная таблица</span>
          <div className="city-table">
            {transportMixRows.length ? (
              transportMixRows.map((item) => (
                <div key={item.label} className="city-table-row">
                  <strong>{item.label}</strong>
                  <span>{item.value}</span>
                </div>
              ))
            ) : (
              <div className="city-table-row">
                <strong>Пока нет</strong>
                <span>Добавим после появления билетов</span>
              </div>
            )}
          </div>
        </div>

        <div className="mini-card city-table-card">
          <span>Профиль узлов</span>
          <div className="city-table">
            <div className="city-table-row">
              <strong>Международный аэропорт</strong>
              <span>{city.has_international_airport ? "Да" : "Нет"}</span>
            </div>
            <div className="city-table-row">
              <strong>Ж/д хаб</strong>
              <span>{city.is_rail_hub ? "Да" : "Нет"}</span>
            </div>
            <div className="city-table-row">
              <strong>Автобусный хаб</strong>
              <span>{city.is_bus_hub ? "Да" : "Нет"}</span>
            </div>
          </div>
        </div>

        <div className="mini-card city-table-card">
          <span>Популярные направления</span>
          <div className="city-table">
            {popularRoutes.length ? (
              popularRoutes.slice(0, 6).map((name) => (
                <div key={name} className="city-table-row">
                  <strong>{name}</strong>
                  <span>Активное направление</span>
                </div>
              ))
            ) : (
              <div className="city-table-row">
                <strong>Пока нет</strong>
                <span>Направления появятся вместе с билетами</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </Wrapper>
  );
}
