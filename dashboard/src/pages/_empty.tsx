export function EmptyPage({ title, body }: { title: string; body: string }) {
  return (
    <div style={{ maxWidth: 640 }}>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>{title}</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-3)" }}>{body}</p>
    </div>
  );
}
