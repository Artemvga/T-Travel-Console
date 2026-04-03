export function ErrorState({ title, message, action = null }) {
  return (
    <section className="state-card state-card-error">
      <div className="state-mark">!</div>
      <div className="state-copy">
        <h3>{title}</h3>
        <p>{message}</p>
      </div>
      {action ? <div>{action}</div> : null}
    </section>
  );
}
