export function formatPrice(value) {
  return `${new Intl.NumberFormat("ru-RU").format(value)} ₽`;
}

export function formatCompactNumber(value) {
  return new Intl.NumberFormat("ru-RU", {
    notation: "compact",
    maximumFractionDigits: value >= 1000000 ? 1 : 0,
  }).format(value);
}

export function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  if (!hours) {
    return `${mins} мин`;
  }
  if (!mins) {
    return `${hours} ч`;
  }
  return `${hours} ч ${mins} мин`;
}

export function formatDateTime(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatDurationBetween(start, end) {
  const diff = Math.max(0, new Date(end).getTime() - new Date(start).getTime());
  return formatDuration(Math.round(diff / 60000));
}
