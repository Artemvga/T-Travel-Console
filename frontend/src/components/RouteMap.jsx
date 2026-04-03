import { useEffect, useRef, useState } from "react";

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

let yandexMapsPromise = null;

function waitForReady(ymaps) {
  return new Promise((resolve) => {
    ymaps.ready(() => resolve(ymaps));
  });
}

function asPromise(vowLike) {
  return new Promise((resolve, reject) => {
    vowLike.then(resolve, reject);
  });
}

function loadYandexMaps(apiKey) {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("window is not available"));
  }

  if (window.ymaps) {
    return Promise.resolve(window.ymaps);
  }

  if (yandexMapsPromise) {
    return yandexMapsPromise;
  }

  yandexMapsPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector('script[data-yandex-maps="true"]');
    const handleLoad = () => {
      if (window.ymaps) {
        resolve(window.ymaps);
        return;
      }
      reject(new Error("Yandex Maps API loaded without ymaps object"));
    };
    const handleError = () => reject(new Error("Failed to load Yandex Maps API"));

    if (existingScript) {
      existingScript.addEventListener("load", handleLoad, { once: true });
      existingScript.addEventListener("error", handleError, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU&load=package.full`;
    script.async = true;
    script.dataset.yandexMaps = "true";
    script.addEventListener("load", handleLoad, { once: true });
    script.addEventListener("error", handleError, { once: true });
    document.body.appendChild(script);
  });

  return yandexMapsPromise;
}

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
      strokeColor: transportColors[segment.transport_type] || "#141414",
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

function styleRoadRoute(route, color) {
  route.getPaths?.().options.set({
    strokeColor: color,
    strokeWidth: 5,
    opacity: 0.92,
  });
  route.getWayPoints?.().options.set({
    visible: false,
  });
}

function addRoadRoute(ymaps, mapInstance, segment) {
  return asPromise(
    ymaps.route([segment.from_coordinates, segment.to_coordinates], {
      routingMode: "auto",
      mapStateAutoApply: false,
    }),
  )
    .then((route) => {
      styleRoadRoute(route, transportColors[segment.transport_type] || "#686868");
      mapInstance.geoObjects.add(route);
      return route;
    })
    .catch(() => addFallbackLine(ymaps, mapInstance, segment));
}

function addTransitRoute(ymaps, mapInstance, segment) {
  if (!ymaps.multiRouter?.MultiRoute) {
    return Promise.resolve(
      addFallbackLine(ymaps, mapInstance, segment, {
        coordinates: createArcPath(
          segment.from_coordinates,
          segment.to_coordinates,
          0.05,
        ),
        strokeWidth: 4,
        strokeOpacity: 0.85,
      }),
    );
  }

  return new Promise((resolve, reject) => {
    const multiRoute = new ymaps.multiRouter.MultiRoute(
      {
        referencePoints: [
          segment.from_coordinates,
          segment.to_coordinates,
        ],
        params: {
          routingMode: "masstransit",
          results: 1,
        },
      },
      {
        boundsAutoApply: false,
        wayPointVisible: false,
        viaPointVisible: false,
        pinVisible: false,
        routeActiveStrokeColor: transportColors[segment.transport_type] || "#141414",
        routeActiveStrokeWidth: 5,
        routeActiveStrokeOpacity: 0.95,
      },
    );

    let settled = false;
    const handleSuccess = () => {
      if (settled) {
        return;
      }
      settled = true;
      mapInstance.geoObjects.add(multiRoute);
      resolve(multiRoute);
    };
    const handleFail = () => {
      if (settled) {
        return;
      }
      settled = true;
      reject(new Error("Failed to build transit route"));
    };

    multiRoute.model.events.add("requestsuccess", handleSuccess);
    multiRoute.model.events.add("requestfail", handleFail);
  }).catch(() =>
    addFallbackLine(ymaps, mapInstance, segment, {
      coordinates: createArcPath(
        segment.from_coordinates,
        segment.to_coordinates,
        0.05,
      ),
      strokeWidth: 4,
      strokeOpacity: 0.85,
    }),
  );
}

function addSegmentRoute(ymaps, mapInstance, segment) {
  if (segment.transport_type === "plane") {
    return addAirRoute(ymaps, mapInstance, segment);
  }

  if (segment.transport_type === "bus") {
    return addRoadRoute(ymaps, mapInstance, segment);
  }

  return addTransitRoute(ymaps, mapInstance, segment);
}

export function RouteMap({ route, title }) {
  const mapContainerRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const apiKey =
    import.meta.env.VITE_YANDEX_MAPS_API_KEY ||
    "8013b162-6b42-4997-9691-77b7074026e0";
  const statusMessage =
    status === "error"
        ? "Не удалось загрузить Yandex Maps API. Проверьте ключ, квоты и доступность сервиса."
        : status === "loading"
          ? "Готовим карту и подтягиваем реальные траектории Яндекса для наземных сегментов..."
          : "";

  useEffect(() => {
    if (!route?.segments?.length || !route?.waypoints?.length) {
      setStatus("empty");
      return undefined;
    }

    let isDisposed = false;
    let mapInstance = null;

    setStatus("loading");

    loadYandexMaps(apiKey)
      .then(waitForReady)
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
            Автобусы строятся по дорогам, для рельсового транспорта сначала
            используем сценарии Яндекс.Карт, а перелеты показываем отдельной дугой.
          </p>
        </div>
        <div className="route-map-legend">
          {Object.entries(transportLabels).map(([key, label]) => (
            <span key={key} className="route-map-legend-item">
              <i
                style={{
                  background: transportColors[key],
                }}
              />
              {label}
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
