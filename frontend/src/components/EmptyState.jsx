export function EmptyState({ title, message, action = null }) {
  return (
    <section className="state-card">
      <div className="state-mark">i</div>
      <div className="state-copy">
        <h3>{title}</h3>
        <p>{message}</p>
      </div>
      {action ? <div>{action}</div> : null}
    </section>
  );
}
