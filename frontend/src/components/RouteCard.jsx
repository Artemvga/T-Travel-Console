import { formatDuration, formatPrice } from "../utils/format";
import { RouteSegmentCard } from "./RouteSegmentCard";

function routeTitle(transfersCount) {
  if (!transfersCount) {
    return "Прямой маршрут";
  }

  return `Маршрут с ${transfersCount} пересадк${transfersCount === 1 ? "ой" : "ами"}`;
}

export function RouteCard({ route, title, highlight = false }) {
  return (
    <article className={`route-card ${highlight ? "route-card-highlight" : ""}`}>
      <div className="route-card-top">
        <div>
          <p className="eyebrow">{title}</p>
          <h3>
            {routeTitle(route.transfers_count)}
            {highlight ? <span className="route-badge">Рекомендуем</span> : null}
          </h3>
        </div>
        <div className="route-price">{formatPrice(route.total_price)}</div>
      </div>

      {route.waypoints?.length ? (
        <div className="route-waypoints">
          {route.waypoints.map((waypoint) => waypoint.name).join(" • ")}
        </div>
      ) : null}

      <div className="route-summary-grid">
        <div className="mini-card">
          <span>Общее время</span>
          <strong>{formatDuration(route.total_duration_minutes)}</strong>
        </div>
        <div className="mini-card">
          <span>Расстояние</span>
          <strong>{route.total_distance_km} км</strong>
        </div>
        <div className="mini-card">
          <span>Пересадки</span>
          <strong>{route.transfers_count}</strong>
        </div>
        <div className="mini-card">
          <span>Сегменты</span>
          <strong>{route.segments.length}</strong>
        </div>
      </div>

      <div className="segments-list">
        {route.segments.map((segment, index) => (
          <RouteSegmentCard
            key={segment.external_id}
            segment={segment}
            index={index}
          />
        ))}
      </div>
    </article>
  );
}
