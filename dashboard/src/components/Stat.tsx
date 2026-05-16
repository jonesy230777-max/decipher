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
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5)",
      }}
    >
      <div className="hig-footnote" style={{ marginBottom: "var(--space-2)" }}>{label}</div>
      <div className="hig-large-title" style={{ color: "var(--colour-label)" }}>
        {value}
      </div>
      {hint && (
        <div className="hig-caption-1" style={{ marginTop: "var(--space-2)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}
