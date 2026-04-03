import { useEffect, useState } from "react";

import { getApiError, searchCities } from "../services/api";

export function SearchAutocomplete({
  label,
  placeholder,
  selectedCity,
  onSelect,
  helper = "",
}) {
  const [query, setQuery] = useState(selectedCity?.name || "");
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    setQuery(selectedCity?.name || "");
  }, [selectedCity]);

  useEffect(() => {
    const normalized = query.trim();
    const selectedName = selectedCity?.name?.trim() || "";

    if (!normalized || normalized === selectedName) {
      setSuggestions([]);
      setOpen(false);
      setLoading(false);
      return undefined;
    }

    setOpen(true);
    let isCancelled = false;

    const timeoutId = window.setTimeout(async () => {
      setLoading(true);
      setError("");

      try {
        const results = await searchCities(normalized);
        if (isCancelled) {
          return;
        }
        setSuggestions(results);
        setOpen(true);
        setActiveIndex(-1);
      } catch (requestError) {
        if (isCancelled) {
          return;
        }
        setSuggestions([]);
        setOpen(true);
        setError(getApiError(requestError, "Не удалось загрузить подсказки городов."));
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }, 350);

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [query, selectedCity]);

  const handleSelect = (city) => {
    setQuery(city.name);
    setSuggestions([]);
    setOpen(false);
    setError("");
    onSelect(city);
  };

  const handleKeyDown = (event) => {
    if (!open || !suggestions.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((value) => (value + 1) % suggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((value) =>
        value <= 0 ? suggestions.length - 1 : value - 1,
      );
      return;
    }

    if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      handleSelect(suggestions[activeIndex]);
    }
  };

  return (
    <div className="autocomplete-field">
      <label>{label}</label>
      <div className="autocomplete-input-shell">
        <span className="autocomplete-icon">⌕</span>
        <input
          type="text"
          value={query}
          placeholder={placeholder}
          onChange={(event) => {
            const nextValue = event.target.value;
            setQuery(nextValue);
            setOpen(Boolean(nextValue.trim()));
            setError("");
            onSelect(null);
          }}
          onFocus={() => setOpen(Boolean(query.trim() || suggestions.length))}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />
        {selectedCity ? (
          <button
            type="button"
            className="autocomplete-clear"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              setQuery("");
              setSuggestions([]);
              setOpen(false);
              setError("");
              onSelect(null);
            }}
            aria-label="Очистить город"
          >
            ×
          </button>
        ) : null}
      </div>

      {helper ? <p className="field-helper">{helper}</p> : null}

      {open && (loading || suggestions.length || error) ? (
        <div className="autocomplete-dropdown">
          {loading ? <span>Ищем города...</span> : null}
          {!loading && error ? <span>{error}</span> : null}
          {!loading && !error && !suggestions.length ? (
            <span>Совпадений пока нет</span>
          ) : null}
          {!loading &&
            !error &&
            suggestions.map((city, index) => (
              <button
                key={city.slug}
                type="button"
                className={`autocomplete-item ${
                  activeIndex === index ? "autocomplete-item-active" : ""
                }`}
                onMouseDown={() => handleSelect(city)}
              >
                <strong>{city.name}</strong>
                <small>
                  {city.region}
                  {city.population
                    ? ` • ${new Intl.NumberFormat("ru-RU").format(city.population)} чел.`
                    : ""}
                </small>
              </button>
            ))}
        </div>
      ) : null}
    </div>
  );
}
