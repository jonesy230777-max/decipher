/**
 * Tiny inline sparkline. Pure SVG, no chart library overhead.
 * HIG-aligned: uses semantic colour tokens, no gridlines, no labels.
 */
type Props = {
  data: number[];
  width?: number;
  height?: number;
  colour?: string;
};

export function Sparkline({
  data, width = 64, height = 18, colour = "var(--colour-accent)",
}: Props) {
  if (!data || data.length < 2) {
    return <span style={{ display: "inline-block", width, height }} />;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const stepX = width / (data.length - 1);
  const points = data.map((v, i) => {
    const x = i * stepX;
    const y = height - 2 - ((v - min) / span) * (height - 4);
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
  const lastX = (data.length - 1) * stepX;
  const lastY = height - 2 - ((data[data.length - 1] - min) / span) * (height - 4);
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: "block" }}
      role="img"
      aria-label={`Sparkline trend, latest ${data[data.length - 1]}`}
    >
      <polyline
        fill="none"
        stroke={colour}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
      <circle cx={lastX} cy={lastY} r="1.8" fill={colour} />
    </svg>
  );
}
