const priorities = [
  { value: "optimal", label: "Оптимальный" },
  { value: "cheapest", label: "Дешевле" },
  { value: "fastest", label: "Быстрее" },
];

const transportLabels = {
  plane: "Самолет",
  train: "Поезд",
  bus: "Автобус",
  electric_train: "Электричка",
};

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
    <div className="filters-grid">
      <section className="filter-card">
        <div className="filter-card-header">
          <p className="eyebrow">Приоритет</p>
          <p>Что важнее в итоговой выдаче.</p>
        </div>
        <div className="choice-group">
          {priorities.map((priority) => (
            <label key={priority.value} className="choice-chip">
              <input
                type="radio"
                name="priority"
                value={priority.value}
                checked={values.priority === priority.value}
                onChange={() => onChange("priority", priority.value)}
              />
              <span>{priority.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="filter-card">
        <div className="filter-card-header">
          <p className="eyebrow">Предпочитаемые компании</p>
          <p>Автобусные операторы подбираются автоматически, вручную выбирать их не нужно.</p>
        </div>
        <div className="choice-group carrier-choice-group">
          {visibleCarriers.map((carrier) => (
            <label key={carrier.code} className="choice-chip">
              <input
                type="checkbox"
                checked={values.preferred_carriers.includes(carrier.code)}
                onChange={() => toggleListValue("preferred_carriers", carrier.code)}
              />
              <span>{carrier.name}</span>
            </label>
          ))}
          {!visibleCarriers.length ? (
            <p className="field-helper">Компании еще загружаются.</p>
          ) : null}
        </div>
      </section>

      <section className="filter-card">
        <div className="filter-card-header">
          <p className="eyebrow">Виды транспорта</p>
          <p>Оставьте пустым, если хотите увидеть полный микс вариантов.</p>
        </div>
        <div className="choice-group">
          {Object.entries(transportLabels).map(([value, label]) => (
            <label key={value} className="choice-chip">
              <input
                type="checkbox"
                checked={values.preferred_transport_types.includes(value)}
                onChange={() =>
                  toggleListValue("preferred_transport_types", value)
                }
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="filter-card">
        <div className="filter-card-header">
          <p className="eyebrow">Дополнительно</p>
          <p>Быстрые ограничения для более узкого сценария поиска.</p>
        </div>
        <div className="settings-grid">
          <label className="switch-row">
            <input
              type="checkbox"
              checked={values.direct_only}
              disabled={transitLocked}
              onChange={(event) => {
                const checked = event.target.checked;
                onChange("direct_only", checked);
                if (checked) {
                  onChange("allow_transfers", false);
                  onChange("max_transfers", 0);
                }
              }}
            />
            <span>Только прямые маршруты</span>
          </label>

          <label className="switch-row">
            <input
              type="checkbox"
              checked={values.allow_transfers}
              disabled={values.direct_only || transitLocked}
              onChange={(event) => onChange("allow_transfers", event.target.checked)}
            />
            <span>Разрешить пересадки</span>
          </label>

          <label className="field-stack">
            <span>Максимум пересадок</span>
            <input
              type="number"
              min="0"
              max="5"
              value={values.max_transfers}
              disabled={!values.allow_transfers || values.direct_only}
              onChange={(event) =>
                onChange("max_transfers", Number(event.target.value))
              }
            />
          </label>

          {transitLocked ? (
            <p className="field-helper">
              Для маршрута через выбранный транзитный город пересадки включены автоматически.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
