export function TransportGlyph({ type, className = "" }) {
  const glyphClassName = `transport-glyph ${className}`.trim();

  if (type === "plane") {
    return (
      <svg viewBox="0 0 24 24" className={`${glyphClassName} transport-glyph-plane`} aria-hidden="true">
        <path
          d="M21.8 11.7c0-.4-.3-.7-.7-.8l-6.5-1.9-3.6-5.3c-.2-.3-.5-.4-.8-.4h-1c-.4 0-.8.3-.8.8l.8 5-4.1-1.2-1.5-2c-.2-.2-.4-.3-.7-.3H2c-.5 0-.9.5-.7 1l1.3 3.2-1.3 3.2c-.2.5.2 1 .7 1h.8c.3 0 .5-.1.7-.3l1.5-2 4.1-1.2-.8 5c-.1.5.3.8.8.8h1c.3 0 .6-.1.8-.4l3.6-5.3 6.5-1.9c.4-.1.7-.4.7-.8Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (type === "train") {
    return (
      <svg viewBox="0 0 24 24" className={`${glyphClassName} transport-glyph-train`} aria-hidden="true">
        <path
          d="M7 3h10c2.2 0 4 1.8 4 4v6.8c0 1.6-.9 3-2.3 3.7l1.8 2.5H18l-1.2-1.7H7.2L6 20H3.5l1.8-2.5A4.1 4.1 0 0 1 3 13.8V7c0-2.2 1.8-4 4-4Zm0 2a2 2 0 0 0-2 2v5h14V7a2 2 0 0 0-2-2H7Zm1 2h3v3H8V7Zm5 0h3v3h-3V7Zm-5.5 8a1.5 1.5 0 1 0 0-.1V15Zm9 0a1.5 1.5 0 1 0 0-.1V15ZM6 17h12v-2H6v2Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (type === "bus") {
    return (
      <svg viewBox="0 0 24 24" className={`${glyphClassName} transport-glyph-bus`} aria-hidden="true">
        <path
          d="M6 4h12c2.2 0 4 1.8 4 4v7c0 1.7-1 3.1-2.5 3.7V21H17v-2H7v2H4.5v-2.3A4 4 0 0 1 2 15V8c0-2.2 1.8-4 4-4Zm0 2a2 2 0 0 0-2 2v4h16V8a2 2 0 0 0-2-2H6Zm1 1h4v3H7V7Zm6 0h4v3h-4V7ZM6.5 16.8a1.6 1.6 0 1 0 0-.1v.1Zm11 0a1.6 1.6 0 1 0 0-.1v.1ZM4 14v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1H4Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className={`${glyphClassName} transport-glyph-electric`} aria-hidden="true">
      <path
        d="M13.4 2 6 13h4.6L9.9 22 18 10.8h-4.7L13.4 2Z"
        fill="currentColor"
      />
    </svg>
  );
}
