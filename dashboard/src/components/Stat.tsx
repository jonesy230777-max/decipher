type StatProps = { label: string; value: string | number; hint?: string };

export function Stat({ label, value, hint }: StatProps) {
  return (
    <div
      style={{
        background: "var(--colour-bg-elevated)",
        border: "1px solid var(--colour-border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-4)",
        boxShadow: "var(--shadow-1)",
      }}
    >
      <div
        style={{
          fontSize: "var(--type-subhead)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          color: "var(--colour-text-secondary)",
          marginBottom: "var(--space-2)",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "var(--type-large-title)",
          fontWeight: 700,
          lineHeight: 1.05,
          color: "var(--colour-text-primary)",
        }}
      >
        {value}
      </div>
      {hint && (
        <div
          style={{
            marginTop: "var(--space-2)",
            fontSize: "var(--type-footnote)",
            color: "var(--colour-text-tertiary)",
          }}
        >
          {hint}
        </div>
      )}
    </div>
  );
}
