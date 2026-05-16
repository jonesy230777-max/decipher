type StatProps = { label: string; value: string | number; hint?: string };

/**
 * HIG-style stat tile.
 *  - Label: Footnote secondaryLabel (no uppercase tracking)
 *  - Value: Large Title, SF Pro Display, tabular numerals
 *  - Hint: Caption-1 tertiaryLabel
 */
export function Stat({ label, value, hint }: StatProps) {
  return (
    <div
      style={{
        background: "var(--colour-bg-system-secondary)",
        border: "1px solid var(--colour-separator-opaque)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-3) var(--space-4)",
      }}
    >
      <div className="hig-caption-1" style={{ marginBottom: 2, color: "var(--colour-label-secondary)" }}>
        {label}
      </div>
      <div className="hig-title-2 hig-numeric" style={{ color: "var(--colour-label)", fontWeight: 700 }}>
        {value}
      </div>
      {hint && (
        <div className="hig-caption-1" style={{ marginTop: 2, color: "var(--colour-label-tertiary)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}
