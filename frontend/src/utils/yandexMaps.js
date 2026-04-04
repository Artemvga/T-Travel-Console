let yandexMapsPromise = null;

export function waitForYandexReady(ymaps) {
  return new Promise((resolve) => {
    ymaps.ready(() => resolve(ymaps));
  });
}

export function loadYandexMaps(apiKey) {
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

