import { formatCompactNumber } from "../utils/format";

const transportLabels = {
  bus: "Автобус",
  train: "Поезд",
  plane: "Самолет",
  electric_train: "Электричка",
};

const transportIcons = {
  bus: "BUS",
  train: "ЖД",
  plane: "AIR",
  electric_train: "ЭЛ",
};

function HubCard({ code, label, active }) {
  return (
    <article className={`hub-card ${active ? "hub-card-active" : "hub-card-muted"}`}>
      <span className="hub-card-icon">{code}</span>
      <div>
        <strong>{label}</strong>
        <p>{active ? "Доступно" : "Нет данных"}</p>
      </div>
    </article>
  );
}

export function CityInfoCard({ city }) {
  const hubCards = [
    { code: "BUS", label: "Автобусная станция", active: city.has_bus_station },
    { code: "AIR", label: "Аэропорт", active: city.has_airport },
    { code: "ЖД", label: "Ж/д станция", active: city.has_train_station },
    {
      code: "ЭЛ",
      label: "Электрички",
      active: city.has_commuter_station,
    },
  ];

  return (
    <section className="info-card city-info-card-live">
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
            Видно транспортные узлы, объём витрины билетов и самые частые
            направления для этого города.
          </p>
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
            code={item.code}
            label={item.label}
            active={item.active}
          />
        ))}
      </div>

      <div className="transport-tags transport-tags-live">
        {city.available_transports.map((item) => (
          <span key={item} className="transport-tag transport-tag-live">
            <span className="transport-tag-icon">
              {transportIcons[item] || "TR"}
            </span>
            {transportLabels[item] || item}
          </span>
        ))}
      </div>

      <div className="info-grid info-grid-live">
        <div className="mini-card">
          <span>Транспортный микс</span>
          <strong>
            {city.tickets_by_transport?.length
              ? city.tickets_by_transport
                  .map(
                    (item) =>
                      `${transportLabels[item.transport_type] || item.transport_type}: ${formatCompactNumber(item.tickets_count)}`,
                  )
                  .join(" • ")
              : "Пока нет"}
          </strong>
        </div>
        <div className="mini-card">
          <span>Координаты</span>
          <strong>
            {city.latitude}, {city.longitude}
          </strong>
        </div>
        <div className="mini-card">
          <span>Популярные направления</span>
          <strong>
            {city.popular_destinations?.length
              ? city.popular_destinations
                  .map((item) => `${item.name} (${formatCompactNumber(item.tickets_count || 0)})`)
                  .join(", ")
              : "Пока нет"}
          </strong>
        </div>
      </div>
    </section>
  );
}
