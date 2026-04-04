import { useEffect, useRef, useState } from "react";

import { loadYandexMaps, waitForYandexReady } from "../utils/yandexMaps";
import { formatDuration } from "../utils/format";

const transportColors = {
  plane: "#ffcf19",
  train: "#111111",
  bus: "#666666",
  electric_train: "#c9a700",
};

const transportLabels = {
  plane: "Самолет",
  train: "Поезд",
  bus: "Автобус",
  electric_train: "Электричка",
};

function createArcPath(from, to, curveFactor = 0.16) {
  const [lat1, lon1] = from;
  const [lat2, lon2] = to;
  const midLat = (lat1 + lat2) / 2;
  const midLon = (lon1 + lon2) / 2;
  const deltaLat = lat2 - lat1;
  const deltaLon = lon2 - lon1;
  const controlLat = midLat - deltaLon * curveFactor;
  const controlLon = midLon + deltaLat * curveFactor;
  const points = [];

  for (let step = 0; step <= 24; step += 1) {
    const t = step / 24;
    const lat =
      (1 - t) * (1 - t) * lat1 + 2 * (1 - t) * t * controlLat + t * t * lat2;
    const lon =
      (1 - t) * (1 - t) * lon1 + 2 * (1 - t) * t * controlLon + t * t * lon2;
    points.push([lat, lon]);
  }

  return points;
}

function addFallbackLine(ymaps, mapInstance, segment, options = {}) {
  const strokeColor =
    options.strokeColor || segment.visual?.color || transportColors[segment.transport_type] || "#141414";
  const coords =
    options.coordinates ||
    [segment.from_coordinates, segment.to_coordinates];

  const line = new ymaps.Polyline(
    coords,
    {
      balloonContentHeader: `${segment.from_city} → ${segment.to_city}`,
      balloonContentBody: `${transportLabels[segment.transport_type] || segment.transport_type} • ${segment.carrier}`,
    },
    {
      strokeColor,
      strokeWidth: options.strokeWidth || 5,
      strokeOpacity: options.strokeOpacity || 0.92,
      strokeStyle: options.strokeStyle,
      geodesic: Boolean(options.geodesic),
    },
  );
  mapInstance.geoObjects.add(line);
  return line;
}

function addAirRoute(ymaps, mapInstance, segment) {
  return Promise.resolve(
    addFallbackLine(ymaps, mapInstance, segment, {
      coordinates: createArcPath(
        segment.from_coordinates,
        segment.to_coordinates,
      ),
      strokeWidth: 4,
      strokeOpacity: 0.95,
      strokeStyle: "dash",
    }),
  );
}

function addGroundRoute(ymaps, mapInstance, segment) {
  const curveFactor =
    segment.transport_type === "train"
      ? 0.05
      : segment.transport_type === "electric_train"
        ? 0.03
        : 0;
  const coordinates =
    curveFactor > 0
      ? createArcPath(segment.from_coordinates, segment.to_coordinates, curveFactor)
      : [segment.from_coordinates, segment.to_coordinates];
  return Promise.resolve(
    addFallbackLine(ymaps, mapInstance, segment, {
      coordinates,
      strokeWidth: segment.transport_type === "bus" ? 5 : 4,
      strokeOpacity: 0.9,
      geodesic: segment.transport_type === "bus",
    }),
  );
}

function addSegmentRoute(ymaps, mapInstance, segment) {
  if (segment.transport_type === "plane") {
    return addAirRoute(ymaps, mapInstance, segment);
  }
  return addGroundRoute(ymaps, mapInstance, segment);
}

function buildTransportLegend(route) {
  if (route?.transport_legend?.length) {
    return route.transport_legend.map((item) => ({
      key: item.transport_type,
      label: item.label,
      duration: formatDuration(item.duration_minutes),
      color: item.color,
    }));
  }

  const totals = new Map();

  (route?.segments || []).forEach((segment) => {
    const current = totals.get(segment.transport_type) || 0;
    totals.set(segment.transport_type, current + (segment.duration_minutes || 0));
  });

  return Object.entries(transportLabels)
    .filter(([key]) => totals.has(key))
    .map(([key, label]) => ({
      key,
      label,
      duration: formatDuration(totals.get(key)),
      color: transportColors[key],
    }));
}

export function RouteMap({ route, title }) {
  const mapContainerRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const apiKey = import.meta.env.VITE_YANDEX_MAPS_API_KEY || "";
  const statusMessage =
    status === "disabled"
      ? "Ключ Yandex Maps не задан. Маршрут остается доступен списком сегментов."
      : status === "error"
        ? "Не удалось загрузить Yandex Maps API. Проверьте ключ и доступность сервиса."
        : status === "loading"
          ? "Готовим карту и рисуем локальную геометрию маршрута..."
          : "";
  const legendItems = buildTransportLegend(route);

  useEffect(() => {
    if (!route?.segments?.length || !route?.waypoints?.length) {
      setStatus("empty");
      return undefined;
    }

    if (!apiKey) {
      setStatus("disabled");
      return undefined;
    }

    let isDisposed = false;
    let mapInstance = null;

    setStatus("loading");

    loadYandexMaps(apiKey)
      .then(waitForYandexReady)
      .then(async (ymaps) => {
        if (isDisposed || !mapContainerRef.current) {
          return;
        }

        mapInstance = new ymaps.Map(mapContainerRef.current, {
          center: route.path_coordinates[0],
          zoom: 4,
          controls: ["zoomControl", "fullscreenControl"],
        });
        mapInstance.behaviors.disable("scrollZoom");

        route.waypoints.forEach((waypoint, index) => {
          const preset =
            index === 0
              ? "islands#blackCircleDotIcon"
              : index === route.waypoints.length - 1
                ? "islands#yellowCircleDotIcon"
                : "islands#grayCircleDotIcon";

          mapInstance.geoObjects.add(
            new ymaps.Placemark(
              [waypoint.latitude, waypoint.longitude],
              {
                balloonContent: waypoint.name,
                hintContent: waypoint.name,
              },
              { preset },
            ),
          );
        });

        await Promise.allSettled(
          route.segments.map((segment) =>
            addSegmentRoute(ymaps, mapInstance, segment),
          ),
        );

        const bounds = mapInstance.geoObjects.getBounds();
        if (bounds) {
          mapInstance.setBounds(bounds, {
            checkZoomRange: true,
            zoomMargin: 28,
          });
        }

        if (!isDisposed) {
          setStatus("ready");
          requestAnimationFrame(() => {
            mapInstance?.container.fitToViewport();
          });
        }
      })
      .catch(() => {
        if (!isDisposed) {
          setStatus("error");
        }
      });

    return () => {
      isDisposed = true;
      if (mapInstance) {
        mapInstance.destroy();
      }
    };
  }, [apiKey, route]);

  return (
    <section className="route-map-card">
      <div className="route-map-header">
        <div>
          <p className="eyebrow">Карта маршрута</p>
          <h3>{title}</h3>
          <p className="route-map-subtitle">
            Карта использует только локальные координаты сегментов: наземные
            участки рисуются линиями, а перелеты показываются отдельной дугой.
          </p>
        </div>
        <div className="route-map-legend">
          {legendItems.map(({ key, label, duration, color }) => (
            <span key={key} className="route-map-legend-item">
              <i
                style={{
                  background: color || transportColors[key],
                }}
              />
              <strong>{label}</strong>
              <small>{duration}</small>
            </span>
          ))}
        </div>
      </div>

      <div className="route-map-shell">
        <div ref={mapContainerRef} className="route-map" />
        {status !== "ready" ? (
          <div className="route-map-placeholder">
            {statusMessage || "Маршрут на карте пока недоступен."}
          </div>
        ) : null}
      </div>
    </section>
  );
}
