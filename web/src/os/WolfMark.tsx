/** Canonical AetherOS wolf mark. The wolf is the ONE primary visual symbol. */
export function WolfMark({
  size = 28,
  title = "AetherOS",
  className,
  style,
}: {
  size?: number;
  title?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      role="img"
      aria-label={title}
      className={className}
      style={style}
    >
      <defs>
        <linearGradient id="aether-wolf-g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0" stopColor="#35E0FF" />
          <stop offset="0.52" stopColor="#3B82F6" />
          <stop offset="1" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
      <path
        fillRule="evenodd"
        fill="url(#aether-wolf-g)"
        d="M256 494L198 420L182 376L88 380L116 308L38 288L124 144L112 120L168 10L212 58L300 58L344 10L400 120L388 144L474 288L396 308L424 380L330 376L314 420Z M128 212L206 240L198 268L136 246Z M384 212L306 240L314 268L376 246Z M256 390L288 424L256 459L224 424Z M256 132L276 158L256 184L236 158Z"
      />
    </svg>
  );
}

export function WolfWordmark({ compact = false }: { compact?: boolean }) {
  return (
    <span
      style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
      aria-label="AetherOS — AI Operating System"
    >
      <WolfMark size={compact ? 20 : 26} />
      <span
        style={{
          fontWeight: 800,
          letterSpacing: "0.14em",
          fontSize: compact ? 12 : 14,
          textTransform: "uppercase",
        }}
      >
        AetherOS
      </span>
    </span>
  );
}
