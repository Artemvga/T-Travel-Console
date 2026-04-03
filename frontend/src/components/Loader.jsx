export function Loader({ text = "Загрузка..." }) {
  return (
    <div className="loader-card" role="status" aria-live="polite">
      <div className="loader-dot" />
      <p>{text}</p>
    </div>
  );
}
