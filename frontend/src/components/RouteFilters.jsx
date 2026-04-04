import { TransportGlyph } from "./TransportGlyph";

const transportOptions = [
  { value: "plane", label: "Самолет" },
  { value: "train", label: "Поезд" },
  { value: "bus", label: "Автобус" },
  { value: "electric_train", label: "Электричка" },
];

export function RouteFilters({
  carriers,
  values,
  onChange,
  transitLocked = false,
}) {
  const visibleCarriers = carriers.filter((carrier) => carrier.transport_type !== "bus");

  const toggleListValue = (field, value) => {
    const currentValues = values[field];
    const nextValues = currentValues.includes(value)
      ? currentValues.filter((item) => item !== value)
      : [...currentValues, value];
    onChange(field, nextValues);
  };

  return (
    <div className="filter-table-grid">
      <section className="filter-table-cell">
        <div className="filter-card-header">
          <p className="eyebrow">Компании</p>
          <p>Автобусных операторов выбираем автоматически, вручную доступны авиа и ж/д.</p>
        </div>
        <div className="choice-group carrier-choice-group">
          {visibleCarriers.map((carrier) => (
            <label
              key={carrier.code}
              className={`choice-chip ${
                values.preferred_carriers.includes(carrier.code) ? "choice-chip-active" : ""
              }`}
            >
              <input
                type="checkbox"
                checked={values.preferred_carriers.includes(carrier.code)}
                onChange={() => toggleListValue("preferred_carriers", carrier.code)}
              />
              <span>{carrier.name}</span>
            </label>
          ))}
          {!visibleCarriers.length ? (
            <p className="field-helper">Компании появятся после загрузки витрины.</p>
          ) : null}
        </div>
      </section>

      <section className="filter-table-cell">
        <div className="filter-card-header">
          <p className="eyebrow">Транспорт</p>
          <p>Оставьте только нужные типы транспорта, если хотите сузить выдачу.</p>
        </div>
        <div className="choice-group choice-group-compact transport-choice-grid">
          {transportOptions.map((option) => (
            <label
              key={option.value}
              className={`choice-chip choice-chip-transport ${
                values.preferred_transport_types.includes(option.value)
                  ? "choice-chip-active"
                  : ""
              }`}
            >
              <input
                type="checkbox"
                checked={values.preferred_transport_types.includes(option.value)}
                onChange={() =>
                  toggleListValue("preferred_transport_types", option.value)
                }
              />
              <span className="choice-chip-icon choice-chip-icon-glyph">
                <TransportGlyph type={option.value} />
              </span>
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="filter-table-cell">
        <div className="filter-card-header">
          <p className="eyebrow">Режим маршрута</p>
          <p>Выберите прямой путь или поиск со стыковками. Для транзита пересадки включаются сами.</p>
        </div>

        <div className="toggle-row">
          <button
            type="button"
            className={`toggle-pill ${values.direct_only ? "toggle-pill-active" : ""}`}
            disabled={transitLocked}
            onClick={() => {
              onChange("direct_only", true);
              onChange("allow_transfers", false);
              onChange("max_transfers", 0);
            }}
          >
            Без пересадок
          </button>
          <button
            type="button"
            className={`toggle-pill ${values.allow_transfers && !values.direct_only ? "toggle-pill-active" : ""}`}
            onClick={() => {
              onChange("direct_only", false);
              onChange("allow_transfers", true);
              if (!values.max_transfers) {
                onChange("max_transfers", transitLocked ? 1 : 1);
              }
            }}
          >
            С пересадками
          </button>
        </div>

        {values.allow_transfers && !values.direct_only ? (
          <div className="field-stack route-transfers-stack">
            <span>Максимум пересадок</span>
            <div className="transfer-chip-group">
              {[1, 2, 3, 4, 5].map((count) => {
                return (
                  <button
                    key={count}
                    type="button"
                    className={`transfer-chip ${values.max_transfers === count ? "transfer-chip-active" : ""}`}
                    onClick={() => onChange("max_transfers", count)}
                  >
                    {count}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {transitLocked ? (
          <p className="field-helper">
            Транзитный город выбран, поэтому система оставляет минимум одну пересадку.
          </p>
        ) : null}
      </section>
    </div>
  );
}
