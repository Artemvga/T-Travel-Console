import { useState } from "react";

import { CityInfoCard } from "../components/CityInfoCard";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Footer } from "../components/Footer";
import { Loader } from "../components/Loader";
import { Navbar } from "../components/Navbar";
import { SearchAutocomplete } from "../components/SearchAutocomplete";
import { visuals } from "../content/visuals";
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
        <section className="content-card content-card-search city-search-card">
          <div className="city-search-layout">
            <form className="city-search-form" onSubmit={handleSubmit}>
              <div className="section-head">
                <div>
                  <p className="eyebrow">Информация о городе</p>
                  <h2>Найдите город и сразу проверьте его транспортный профиль.</h2>
                </div>
              </div>
              <p className="page-copy">
                Покажем население, регион, инфраструктуру, активность по билетам
                и направления, в которых город чаще всего участвует.
              </p>
              <SearchAutocomplete
                label="Город"
                placeholder="Например, Новосибирск"
                selectedCity={selectedCity}
                onSelect={handleSelect}
                helper="Можно искать по полному названию, части названия и популярным сокращениям."
              />
              <div className="form-actions">
                <button type="submit" className="primary-button" disabled={!selectedCity || loading}>
                  {loading ? "Загружаем..." : "Показать информацию"}
                </button>
              </div>
            </form>

            <div className="city-search-visual">
              <img src={visuals.hero} alt="Городской пейзаж" />
            </div>
          </div>
        </section>

        {loading ? <Loader text="Загружаем информацию о городе..." /> : null}

        {!loading && error ? (
          <ErrorState
            title="Не удалось получить данные"
            message={error}
          />
        ) : null}

        {!loading && !error && cityDetail ? <CityInfoCard city={cityDetail} /> : null}

        {!loading && !error && !cityDetail ? (
          <EmptyState
            title="Город пока не выбран"
            message="Найдите город через поиск и нажмите кнопку, чтобы увидеть полную карточку."
          />
        ) : null}
      </main>

      <Footer />
    </div>
  );
}
