import type { ReactNode } from "react";

export function Card({ children, title, action }: { children: ReactNode; title?: string; action?: ReactNode }) {
  return (
    <section
      style={{
        background: "var(--colour-bg-elevated)",
        border: "1px solid var(--colour-border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-5)",
        boxShadow: "var(--shadow-1)",
      }}
    >
      {(title || action) && (
        <header
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: "var(--space-4)",
          }}
        >
          {title && (
            <h3 style={{ margin: 0, fontSize: "var(--type-title-3)", fontWeight: 600 }}>{title}</h3>
          )}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function SectionEyebrow({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: "var(--type-subhead)",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        color: "var(--colour-text-secondary)",
      }}
    >
      {children}
    </div>
  );
}

export function Button({
  children,
  onClick,
  href,
  variant = "filled",
  download,
}: {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: "filled" | "tinted" | "plain";
  download?: boolean | string;
}) {
  const base = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-2)",
    padding: "var(--space-3) var(--space-4)",
    minHeight: 44,
    fontSize: "var(--type-callout)",
    fontWeight: 600,
    borderRadius: "var(--radius-sm)",
    border: "1px solid transparent",
    cursor: "pointer",
    textDecoration: "none",
    transition: "background var(--duration-fast) var(--easing)",
  } as const;
  const styles = {
    filled: { ...base, background: "var(--colour-fill-primary)", color: "var(--colour-bg-base)" },
    tinted: { ...base, background: "var(--colour-fill-secondary)", color: "var(--colour-text-primary)" },
    plain:  { ...base, background: "transparent", color: "var(--colour-text-primary)",
              border: "1px solid var(--colour-border-subtle)" },
  }[variant];
  if (href) {
    return (
      <a href={href} download={download} style={styles}>
        {children}
      </a>
    );
  }
  return (
    <button onClick={onClick} style={styles}>
      {children}
    </button>
  );
}
