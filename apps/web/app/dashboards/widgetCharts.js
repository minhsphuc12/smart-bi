"use client";

/**
 * Map result columns to indices using widget hints (case-insensitive substring match).
 */
export function resolveColumnIndexes(columns, xHint, yHint, fieldHint) {
  const lower = (c) => String(c || "").toLowerCase();
  const find = (hint) => {
    if (!hint || !columns?.length) return -1;
    const h = String(hint).toLowerCase();
    let i = columns.findIndex((c) => lower(c) === h);
    if (i >= 0) return i;
    i = columns.findIndex((c) => lower(c).includes(h) || h.includes(lower(c)));
    return i;
  };
  let xi = find(xHint);
  let yi = find(yHint);
  if (xi < 0) xi = 0;
  if (yi < 0) yi = columns.length > 1 ? 1 : 0;
  if (yi === xi && columns.length > 1) yi = xi === 0 ? 1 : 0;
  let fi = find(fieldHint);
  if (fi < 0) fi = columns.length > 1 ? 1 : 0;
  return { xi, yi, fi };
}

function toNumber(v) {
  if (v === null || v === undefined) return NaN;
  if (typeof v === "number" && Number.isFinite(v)) return v;
  const n = Number(String(v).replace(/,/g, ""));
  return Number.isFinite(n) ? n : NaN;
}

function buildNumericSeries(columns, rows, xi, yi, maxPoints) {
  if (!rows?.length || !columns?.length) return [];
  const out = [];
  for (let r = 0; r < rows.length && out.length < maxPoints; r++) {
    const row = rows[r];
    const xv = row[xi];
    const yv = toNumber(row[yi]);
    if (!Number.isFinite(yv)) continue;
    out.push({ xLabel: String(xv ?? ""), y: yv });
  }
  return out;
}

function SvgChartFrame({ width, height, children }) {
  return (
    <svg
      width="100%"
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: "block", maxHeight: 200 }}
      role="img"
      aria-hidden
    >
      {children}
    </svg>
  );
}

export function WidgetAreaChart({ columns, rows, xHint, yHint, variant }) {
  const { xi, yi } = resolveColumnIndexes(columns, xHint, yHint, "");
  const series = buildNumericSeries(columns, rows, xi, yi, 120);
  const W = 320;
  const H = 140;
  const pad = { t: 8, r: 8, b: 22, l: 36 };
  const iw = W - pad.l - pad.r;
  const ih = H - pad.t - pad.b;
  if (!series.length) {
    return <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>No numeric points to plot.</p>;
  }
  const ys = series.map((p) => p.y);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const ySpan = maxY - minY || 1;
  const n = series.length;
  const xAt = (i) => pad.l + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw);
  const yAt = (y) => pad.t + ih - ((y - minY) / ySpan) * ih;
  const points = series.map((p, i) => `${xAt(i)},${yAt(p.y)}`).join(" ");
  const baseY = pad.t + ih;
  const areaPath = `M ${xAt(0)} ${baseY} L ${series.map((p, i) => `${xAt(i)} ${yAt(p.y)}`).join(" L ")} L ${xAt(n - 1)} ${baseY} Z`;
  const stroke =
    variant === "bar"
      ? "var(--accent)"
      : variant === "area"
        ? "color-mix(in srgb, var(--accent) 85%, black)"
        : "var(--accent)";
  if (variant === "bar") {
    const bw = Math.max(4, iw / n - 4);
    return (
      <SvgChartFrame width={W} height={H}>
        <line x1={pad.l} y1={baseY} x2={W - pad.r} y2={baseY} stroke="var(--border)" strokeWidth={1} />
        {series.map((p, i) => {
          const x = xAt(i) - bw / 2;
          const h = baseY - yAt(p.y);
          return <rect key={i} x={x} y={yAt(p.y)} width={bw} height={h} rx={3} fill="var(--accent)" opacity={0.85} />;
        })}
      </SvgChartFrame>
    );
  }
  if (variant === "area") {
    return (
      <SvgChartFrame width={W} height={H}>
        <path d={areaPath} fill="color-mix(in srgb, var(--accent) 35%, transparent)" stroke="none" />
        <polyline fill="none" stroke={stroke} strokeWidth={2} points={points} />
      </SvgChartFrame>
    );
  }
  return (
    <SvgChartFrame width={W} height={H}>
      <polyline fill="none" stroke={stroke} strokeWidth={2} points={points} />
      <polyline fill="none" stroke="color-mix(in srgb, var(--accent) 40%, transparent)" strokeWidth={4} points={points} opacity={0.35} />
    </SvgChartFrame>
  );
}

export function WidgetKpiValue({ columns, rows, fieldHint }) {
  if (!rows?.length) {
    return <span style={{ fontSize: "1.5rem", fontWeight: 800 }}>—</span>;
  }
  const { fi } = resolveColumnIndexes(columns, "", "", fieldHint);
  const v = rows[0][fi];
  const formatted = typeof v === "number" && Number.isFinite(v) ? v.toLocaleString() : String(v ?? "—");
  return <span style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em" }}>{formatted}</span>;
}

export function WidgetDataTable({ columns, rows, maxRows = 12 }) {
  const slice = rows.slice(0, maxRows);
  return (
    <div className="table-wrap">
      <table className="data" style={{ fontSize: "0.8rem" }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {slice.length ? (
            slice.map((row, idx) => (
              <tr key={idx}>
                {row.map((cell, j) => (
                  <td key={j} className="mono">
                    {String(cell)}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length || 1} style={{ color: "var(--text-muted)" }}>
                No rows
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
