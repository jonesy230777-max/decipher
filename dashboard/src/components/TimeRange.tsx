/**
 * Reusable time-range selector. Standard windows across every page that
 * has graphs. "All" = 5 years (effectively end-of-time for this build).
 */
export const TIME_RANGES = [
  { key: "7",   label: "7 days",  days: 7 },
  { key: "30",  label: "30 days", days: 30 },
  { key: "180", label: "6 months", days: 180 },
  { key: "365", label: "12 months", days: 365 },
  { key: "all", label: "All", days: 365 * 5 },
] as const;
export type TimeRangeKey = typeof TIME_RANGES[number]["key"];

export function TimeRange({ value, onChange }:
  { value: TimeRangeKey; onChange: (v: TimeRangeKey) => void }) {
  return (
    <div
      role="radiogroup"
      aria-label="Time range"
      style={{
        display: "inline-flex",
        gap: 2,
        background: "var(--colour-fill-tertiary)",
        padding: 2,
        borderRadius: "var(--radius-sm)",
      }}
    >
      {TIME_RANGES.map((r) => {
        const active = value === r.key;
        return (
          <button
            key={r.key}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(r.key)}
            className="hig-caption-1"
            style={{
              padding: "6px 12px",
              borderRadius: 4,
              border: "none",
              background: active ? "var(--colour-bg-system)" : "transparent",
              color: "var(--colour-label)",
              fontWeight: active ? 700 : 500,
              cursor: "pointer",
              boxShadow: active ? "var(--shadow-1)" : "none",
              minHeight: 28,
              fontFamily: "inherit",
            }}
          >
            {r.label}
          </button>
        );
      })}
    </div>
  );
}

export function rangeDays(key: TimeRangeKey): number {
  return TIME_RANGES.find((r) => r.key === key)?.days ?? 30;
}
