import type { ReactNode } from "react";

/**
 * HIG card / group container.
 *  - Background: secondarySystemBackground
 *  - Border: hairline separator
 *  - Radius: 14px (HIG card radius)
 *  - Padding: 24 (space-5)
 */
export function Card({
  children, title, action, padding = "var(--space-5)",
}: { children: ReactNode; title?: string; action?: ReactNode; padding?: string }) {
  return (
    <section
      style={{
        background: "var(--colour-bg-system-secondary)",
        border: "1px solid var(--colour-separator-opaque)",
        borderRadius: "var(--radius-lg)",
        padding,
      }}
    >
      {(title || action) && (
        <header
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: "var(--space-4)",
            gap: "var(--space-3)",
          }}
        >
          {title && <h3 className="hig-title-3" style={{ margin: 0 }}>{title}</h3>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

/**
 * HIG section eyebrow — Footnote, secondaryLabel, no all-caps tracking.
 * Apple uses Footnote-weight labels above group headers, not letter-spaced caps.
 */
export function SectionEyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="hig-footnote" style={{ marginBottom: "var(--space-1)" }}>
      {children}
    </div>
  );
}

/**
 * HIG button. Roles:
 *   - filled  = Primary (accent colour, white label)
 *   - tinted  = Secondary (accent tint background, accent label)
 *   - plain   = Tertiary (no background, label colour)
 *   - destructive (accent-red filled)
 * Min tap target 44pt (HIG iOS) / ~28pt control height (macOS push button) — we use 36 minimum here for desktop while keeping 44 for top-level CTAs.
 */
type ButtonVariant = "filled" | "tinted" | "plain" | "ghost" | "destructive";

export function Button({
  children, onClick, href, variant = "filled", download, size = "md", disabled = false,
}: {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: ButtonVariant;
  download?: boolean | string;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
}) {
  const heights = { sm: 28, md: 36, lg: 44 };
  const pad = { sm: "var(--space-2) var(--space-3)",
                md: "var(--space-2) var(--space-4)",
                lg: "var(--space-3) var(--space-5)" }[size];
  const base = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-2)",
    padding: pad,
    minHeight: heights[size],
    fontSize: "var(--type-callout)",
    lineHeight: "var(--lead-callout)",
    fontWeight: 600,
    borderRadius: "var(--radius-sm)",
    border: "1px solid transparent",
    cursor: disabled ? "not-allowed" : "pointer",
    textDecoration: "none",
    opacity: disabled ? 0.45 : 1,
    transition: "background var(--duration-fast) var(--easing), opacity var(--duration-fast) var(--easing)",
  } as const;

  const variants: Record<ButtonVariant, React.CSSProperties> = {
    filled:      { ...base, background: "var(--colour-accent)", color: "#FFFFFF" },
    tinted:      { ...base, background: "var(--colour-accent-tint-bg)", color: "var(--colour-accent)" },
    plain:       { ...base, background: "transparent", color: "var(--colour-label)",
                   border: "1px solid var(--colour-separator-opaque)" },
    ghost:       { ...base, background: "transparent", color: "var(--colour-accent)" },
    destructive: { ...base, background: "var(--colour-system-red)", color: "#FFFFFF" },
  };
  const style = variants[variant];

  if (href) {
    return (
      <a href={href} download={download} style={style}>
        {children}
      </a>
    );
  }
  return (
    <button onClick={disabled ? undefined : onClick} disabled={disabled} style={style}>
      {children}
    </button>
  );
}

/**
 * HIG inline row separator.
 */
export function Separator() {
  return (
    <div
      style={{
        height: 1,
        background: "var(--colour-separator)",
        margin: "var(--space-3) 0",
      }}
    />
  );
}
