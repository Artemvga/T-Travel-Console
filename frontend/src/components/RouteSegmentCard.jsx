import { formatDateTime, formatDurationBetween, formatPrice } from "../utils/format";

const transportLabels = {
  plane: "Самолет",
  train: "Поезд",
  bus: "Автобус",
  electric_train: "Электричка",
};

const transportCodes = {
  plane: "✈",
  train: "ЖД",
  bus: "BUS",
  electric_train: "ЭЛ",
};

export function RouteSegmentCard({ segment, index }) {
  return (
    <article className={`segment-card segment-card-${segment.transport_type}`}>
      <div className="segment-top">
        <div className="segment-title">
          <span className="segment-icon">
            {transportCodes[segment.transport_type] || "TR"}
          </span>
          <div>
            <span className="segment-index">Сегмент {index + 1}</span>
            <strong>{transportLabels[segment.transport_type] || segment.transport_type}</strong>
            <p>{segment.carrier}</p>
          </div>
        </div>
        <span className="transport-tag">
          {formatPrice(segment.price)}
        </span>
      </div>

      <div className="segment-route">
        <div>
          <span>{segment.from_city}</span>
          <strong>{formatDateTime(segment.departure_datetime)}</strong>
        </div>
        <span className="segment-arrow">→</span>
        <div>
          <span>{segment.to_city}</span>
          <strong>{formatDateTime(segment.arrival_datetime)}</strong>
        </div>
      </div>

      <div className="segment-meta">
        <span>{formatDurationBetween(segment.departure_datetime, segment.arrival_datetime)}</span>
        <span>{segment.distance_km} км</span>
        <span>Мест: {segment.available_seats}</span>
      </div>
    </article>
  );
}
