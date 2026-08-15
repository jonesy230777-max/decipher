import { useMemo, useState, type ReactNode } from "react";

export type Column<T> = {
  key: string;
  label: string;
  align?: "left" | "right";
  sortable?: boolean;                     // default true
  format?: (row: T) => ReactNode;         // custom cell render
  sortValue?: (row: T) => string | number | null | undefined; // override sort key
  style?: React.CSSProperties;
  thStyle?: React.CSSProperties;
};

type Props<T> = {
  rows: T[] | null;
  columns: Column<T>[];
  rowKey: (row: T) => string | number;
  empty?: ReactNode;
  initialSort?: { key: keyof T & string; dir: "asc" | "desc" };
};

/**
 * HIG-aligned sortable table. Every header is a button with a tri-state
 * indicator: ▲ asc · ▼ desc · · unsorted. Rule §18 in CLAUDE.md: all laundry
 * lists must use this; do not write a custom <thead>.
 */
export function SortableTable<T extends Record<string, any>>({
  rows, columns, rowKey, empty, initialSort,
}: Props<T>) {
  const [sortKey, setSortKey] = useState<string | null>(initialSort?.key ?? null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">(initialSort?.dir ?? "desc");

  const sorted = useMemo(() => {
    if (!rows) return null;
    if (!sortKey) return rows;
    const col = columns.find((c) => c.key === sortKey);
    const get = (r: T) => col?.sortValue ? col.sortValue(r) : (r as any)[sortKey];
    const dir = sortDir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = get(a); const vb = get(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
  }, [rows, sortKey, sortDir, columns]);

  function onHeaderClick(k: string) {
    if (sortKey === k) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(k);
      setSortDir("asc");
    }
  }

  if (rows && rows.length === 0) {
    return <p className="hig-footnote" style={{ margin: 0 }}>{empty ?? "Nothing to show."}</p>;
  }

  return (
    <div
      style={{
        background: "var(--colour-bg-system-secondary)",
        border: "1px solid var(--colour-separator-opaque)",
        borderRadius: "var(--radius-lg)",
        overflow: "auto",
      }}
    >
      <table style={{ width: "100%", borderCollapse: "collapse" }} className="hig-callout">
        <thead style={{ background: "var(--colour-fill-quaternary)" }}>
          <tr>
            {columns.map((c) => {
              const active = sortKey === c.key;
              const indicator = !c.sortable && c.sortable !== undefined
                ? ""
                : active
                  ? sortDir === "asc" ? " ▲" : " ▼"
                  : " ·";
              const sortable = c.sortable !== false;
              return (
                <th
                  key={c.key}
                  style={{
                    padding: 0,
                    textAlign: c.align ?? "left",
                    ...c.thStyle,
                  }}
                >
                  <button
                    onClick={() => sortable && onHeaderClick(c.key)}
                    disabled={!sortable}
                    aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                    className="hig-footnote"
                    style={{
                      width: "100%",
                      padding: "var(--space-3)",
                      textAlign: c.align ?? "left",
                      background: "transparent",
                      color: active ? "var(--colour-label)" : "var(--colour-label-secondary)",
                      fontWeight: active ? 700 : 600,
                      border: "none",
                      cursor: sortable ? "pointer" : "default",
                    }}
                  >
                    {c.label}
                    <span aria-hidden="true" style={{ color: "var(--colour-label-tertiary)" }}>
                      {sortable ? indicator : ""}
                    </span>
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted?.map((r) => (
            <tr key={rowKey(r)} style={{ borderTop: "1px solid var(--colour-separator)" }}>
              {columns.map((c) => (
                <td
                  key={c.key}
                  style={{
                    padding: "var(--space-3)",
                    textAlign: c.align ?? "left",
                    ...c.style,
                  }}
                >
                  {c.format ? c.format(r) : (r as any)[c.key] ?? "·"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
