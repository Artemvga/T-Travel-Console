import { useState } from "react";

import { CityMap } from "../components/CityMap";
import { CityInfoCard } from "../components/CityInfoCard";
import { Footer } from "../components/Footer";
import { Navbar } from "../components/Navbar";
import { SearchAutocomplete } from "../components/SearchAutocomplete";
import { getApiError, getCityDetail } from "../services/api";

export function CityInfoPage() {
  const [selectedCity, setSelectedCity] = useState(null);
  const [cityDetail, setCityDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSelect = (city) => {
    setSelectedCity(city);
    setCityDetail(null);
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!selectedCity) {
      setError("Сначала выберите город из подсказок.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const detail = await getCityDetail(selectedCity.slug);
      setCityDetail(detail);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось загрузить информацию о городе."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-shell">
      <Navbar />

      <main className="page">
        <section
          className={`content-card content-card-search city-search-card ${
            cityDetail ? "city-search-card-expanded" : ""
          }`}
        >
          <div className="city-search-layout">
            <form className="city-search-form" onSubmit={handleSubmit}>
              <div className="section-head">
                <div>
                  <p className="eyebrow">Информация о городе</p>
                  <h2>Найдите город и сразу проверьте его транспортный профиль.</h2>
                </div>
              </div>
              <p className="page-copy">
                Покажем население, регион, инфраструктуру, активность по билетам,
                популярные направления и сразу отметим город на Яндекс Карте.
              </p>
              <SearchAutocomplete
                label="Город"
                placeholder="Например, Новосибирск"
                selectedCity={selectedCity}
                onSelect={handleSelect}
                helper="Можно искать по названию, части названия и популярным сокращениям."
              />
              <div className="form-actions">
                <button type="submit" className="primary-button" disabled={!selectedCity || loading}>
                  {loading ? "Загружаем..." : "Показать информацию"}
                </button>
              </div>
            </form>

            <CityMap
              city={cityDetail || selectedCity}
              title={cityDetail?.name || selectedCity?.name || "Выберите город"}
            />
          </div>

          <div className="city-search-panel-state">
            {loading ? (
              <div className="inline-alert">Загружаем информацию о городе...</div>
            ) : null}

            {!loading && error ? (
              <div className="inline-alert inline-alert-error" role="alert">{error}</div>
            ) : null}

            {!loading && !error && !cityDetail ? (
              <div className="city-search-empty-fill">
                <article className="city-search-empty-card">
                  <span>Что появится после выбора</span>
                  <strong>Покажем транспортный профиль, направления, хабы и активность по билетам.</strong>
                </article>
                <article className="city-search-empty-card">
                  <span>Как открыть профиль</span>
                  <strong>Начните вводить город, выберите вариант из выпадающего списка и нажмите кнопку.</strong>
                </article>
                <article className="city-search-empty-card">
                  <span>Карта уже готова</span>
                  <strong>Карта справа подхватит выбранный город и отобразит его без перезагрузки страницы.</strong>
                </article>
              </div>
            ) : null}

            {!loading && !error && cityDetail ? (
              <div className="city-search-expanded-content">
                <CityInfoCard city={cityDetail} embedded />
              </div>
            ) : null}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
