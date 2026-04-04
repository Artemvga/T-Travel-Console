import { useEffect, useRef, useState } from "react";

import { loadYandexMaps, waitForYandexReady } from "../utils/yandexMaps";

export function CityMap({ city, title = "Город на карте", compact = false }) {
  const mapContainerRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const apiKey = import.meta.env.VITE_YANDEX_MAPS_API_KEY || "";

  useEffect(() => {
    if (!city?.latitude || !city?.longitude) {
      setStatus("empty");
      return undefined;
    }

    if (!apiKey) {
      setStatus("disabled");
      return undefined;
    }

    let mapInstance = null;
    let disposed = false;

    setStatus("loading");

    loadYandexMaps(apiKey)
      .then(waitForYandexReady)
      .then((ymaps) => {
        if (disposed || !mapContainerRef.current) {
          return;
        }

        mapInstance = new ymaps.Map(mapContainerRef.current, {
          center: [city.latitude, city.longitude],
          zoom: 9,
          controls: compact ? [] : ["zoomControl"],
        });
        mapInstance.behaviors.disable("scrollZoom");

        const placemark = new ymaps.Placemark(
          [city.latitude, city.longitude],
          {
            hintContent: city.name,
            balloonContent: `${city.name}${city.region ? `, ${city.region}` : ""}`,
          },
          {
            preset: "islands#blackCircleDotIcon",
          },
        );

        const circle = new ymaps.Circle(
          [[city.latitude, city.longitude], 12000],
          {},
          {
            fillColor: "rgba(255, 221, 45, 0.18)",
            strokeColor: "#111111",
            strokeOpacity: 0.9,
            strokeWidth: 2,
          },
        );

        mapInstance.geoObjects.add(circle);
        mapInstance.geoObjects.add(placemark);
        requestAnimationFrame(() => {
          mapInstance?.container.fitToViewport();
        });
        setStatus("ready");
      })
      .catch(() => {
        if (!disposed) {
          setStatus("error");
        }
      });

    return () => {
      disposed = true;
      mapInstance?.destroy();
    };
  }, [apiKey, city, compact]);

  return (
    <section className={`city-map-card ${compact ? "city-map-card-compact" : ""}`}>
      <div className="city-map-header">
        <div>
          <p className="eyebrow">Карта города</p>
          <h3>{title}</h3>
        </div>
        {city?.region ? <span className="transport-tag">{city.region}</span> : null}
      </div>
      <div className="city-map-shell">
        <div ref={mapContainerRef} className="city-map" />
        {status !== "ready" ? (
          <div className="route-map-placeholder">
            {status === "disabled"
              ? "Ключ Yandex Maps не задан."
              : status === "error"
              ? "Не удалось загрузить карту города."
              : status === "loading"
                ? "Загружаем карту города..."
                : "Выберите город, и покажем его на карте."}
          </div>
        ) : null}
      </div>
    </section>
  );
}
