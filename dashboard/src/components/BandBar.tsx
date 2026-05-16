type Props = {
  label: string;
  elite: number;
  performing: number;
  practising: number;
  developing: number;
};

const BAND_COLOUR = {
  elite:       "var(--colour-band-elite)",
  performing:  "var(--colour-band-performing)",
  practising:  "var(--colour-band-practising)",
  developing:  "var(--colour-band-developing)",
} as const;

const BAND_LABELS = {
  elite:       "Elite",
  performing:  "Performing",
  practising:  "Practising",
  developing:  "Developing",
} as const;

export function BandBar({ label, elite, performing, practising, developing }: Props) {
  const total = elite + performing + practising + developing;
  const order = ["elite", "performing", "practising", "developing"] as const;
  const segments = order.map((k) => ({
    key: k,
    n: { elite, performing, practising, developing }[k],
    colour: BAND_COLOUR[k],
    label: BAND_LABELS[k],
  })).filter((s) => s.n > 0);

  return (
    <div style={{ marginBottom: "var(--space-4)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "var(--space-2)",
        }}
      >
        <span className="hig-headline">{label}</span>
        <span className="hig-footnote hig-numeric">{total} reps</span>
      </div>
      <div
        role="img"
        aria-label={`${label}: Elite ${elite}, Performing ${performing}, Practising ${practising}, Developing ${developing}`}
        style={{
          display: "flex",
          height: 28,
          borderRadius: "var(--radius-sm)",
          overflow: "hidden",
          background: "var(--colour-fill-quaternary)",
        }}
      >
        {segments.map((s) => (
          <div
            key={s.key}
            title={`${s.label} ${s.n}`}
            style={{
              flexGrow: s.n,
              flexBasis: 0,
              background: s.colour,
              color: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "var(--type-caption-1)",
              lineHeight: "var(--lead-caption-1)",
              fontWeight: 600,
              fontVariantNumeric: "tabular-nums",
              minWidth: 0,
              padding: "0 6px",
              whiteSpace: "nowrap",
              overflow: "hidden",
            }}
          >
            {s.label} {s.n}
          </div>
        ))}
      </div>
    </div>
  );
}
