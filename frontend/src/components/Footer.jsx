export function Footer() {
  return (
    <footer className="site-footer-shell">
      <div className="site-footer">
        <div className="site-footer-item">
          <strong>Все права защищены</strong>
          <div className="site-footer-note">Маршруты и билеты по России</div>
        </div>
        <div className="site-footer-item">
          <strong>География</strong>
          <span>1100+ городов и единая транспортная витрина</span>
        </div>
        <div className="site-footer-item site-footer-item-brand">
          <img src="/t-travel-logo.png" alt="Т-Путешествия" className="site-footer-logo" />
          <div className="site-footer-brand-copy">
            <strong>Т-Путешествия</strong>
            <span>Карта маршрутов по России</span>
          </div>
        </div>
        <div className="site-footer-item site-footer-item-center">
          <strong>Контакты</strong>
          <span>support@t-travel.ru</span>
        </div>
        <div className="site-footer-item site-footer-item-right">
          <strong>Поддержка</strong>
          <span>+7 (800) 000-00-00</span>
        </div>
      </div>
    </footer>
  );
}
