import { useId } from "react";

import type { AccuracyRow } from "@/lib/data";
import { formatMMDDYYYY } from "@/lib/format";
import type { ChartMetric } from "@/components/chart-metric-toggle";

type Props = {
  rows: AccuracyRow[];
  k?: 10 | 25 | 50;
  metric?: ChartMetric;
};

type Point = { index: number; date: string | null; value: number };

// Tailwind resolves `stroke-*` / `fill-*` colors to the theme CSS variables, so the
// chart follows light and dark. Classes must appear as complete strings.
const SERIES_STYLE = {
  10: { stroke: "stroke-accent-text", fill: "fill-accent-text" },
  25: { stroke: "stroke-teal", fill: "fill-teal" },
  50: { stroke: "stroke-tier-top50", fill: "fill-tier-top50" },
} as const;

const CHART_HEIGHT = 340;
const PADDING = { top: 36, right: 84, bottom: 92, left: 72 };
/** Horizontal room per show; wider charts scroll instead of crushing labels. */
const POINT_SPACING = 48;
const MIN_PLOT_WIDTH = 480;
const X_LABEL_SPACING = 72;

function formatChartValue(value: number, metric: ChartMetric) {
  return metric === "coverage" ? `${Math.round(value * 100)}%` : String(Math.round(value));
}

function pointValue(row: AccuracyRow, k: 10 | 25 | 50, metric: ChartMetric) {
  const recall = k === 10 ? row.recall10 : k === 25 ? row.recall25 : row.recall50;
  const precision = k === 10 ? row.p10 : k === 25 ? row.p25 : row.p50;
  return metric === "coverage" ? recall : precision === null ? null : precision * k;
}

export function RecallChart({ rows, k = 10, metric = "coverage" }: Props) {
  const id = useId();
  const chronological = [...rows].reverse();
  const totalRows = chronological.length;
  const points: Point[] = [];
  chronological.forEach((row, index) => {
    const value = pointValue(row, k, metric);
    if (value !== null) points.push({ index, date: row.showDate, value });
  });

  if (points.length < 2) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-line bg-surface-2 px-4">
        <p className="text-center text-sm text-on-surface-variant">
          Need at least two scored shows to render a chart.
        </p>
      </div>
    );
  }

  const style = SERIES_STYLE[k];
  const measureLabel = metric === "coverage" ? "coverage" : "hits";
  const values = points.map((point) => point.value);
  const maxValue = Math.max(...values);
  const averageValue = values.reduce((sum, value) => sum + value, 0) / values.length;
  const best = points.reduce((top, point) => (point.value > top.value ? point : top));
  const latest = points[points.length - 1];

  // Coverage is bounded by 100%; hits get headroom above the best show so nothing clips.
  const tickStep = metric === "coverage" ? 0.2 : Math.max(1, Math.ceil((maxValue + 1) / 5));
  const tickCount = 5;
  const yMax = tickStep * tickCount;
  const yTicks = Array.from({ length: tickCount + 1 }, (_, i) => i * tickStep);

  const plotWidth = Math.max(MIN_PLOT_WIDTH, (totalRows - 1) * POINT_SPACING);
  const chartWidth = PADDING.left + plotWidth + PADDING.right;
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  const baseline = PADDING.top + plotHeight;
  const xPos = (index: number) =>
    PADDING.left + (index / Math.max(totalRows - 1, 1)) * plotWidth;
  const yPos = (value: number) => PADDING.top + plotHeight - (value / yMax) * plotHeight;

  const labelInterval = Math.max(
    1,
    Math.ceil(X_LABEL_SPACING / (plotWidth / Math.max(totalRows - 1, 1))),
  );
  const xLabels = chronological
    .map((row, index) => ({ index, date: row.showDate }))
    .filter(({ index }) => (totalRows - 1 - index) % labelInterval === 0);

  const titleId = `${id}-title`;
  const descId = `${id}-desc`;
  const title = `Top ${k} ${measureLabel} across the last ${totalRows} shows`;
  const description = `Line chart, oldest show on the left. ${measureLabel} ranges from ${formatChartValue(
    Math.min(...values),
    metric,
  )} to ${formatChartValue(maxValue, metric)} and ends at ${formatChartValue(latest.value, metric)}. The best show is ${
    formatMMDDYYYY(best.date) ?? "unknown"
  } at ${formatChartValue(best.value, metric)}.`;

  return (
    <div className="horizontal-scroll-surface mx-auto w-full max-w-[960px] pb-2">
      <svg
        aria-describedby={descId}
        aria-labelledby={titleId}
        className="block h-auto w-full"
        role="img"
        style={{ minWidth: chartWidth }}
        viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`}
      >
        <title id={titleId}>{title}</title>
        <desc id={descId}>{description}</desc>

        {yTicks.map((tick) => (
          <g key={`grid-${tick}`}>
            <line
              className="stroke-line"
              strokeWidth="1"
              x1={PADDING.left}
              x2={chartWidth - PADDING.right}
              y1={yPos(tick)}
              y2={yPos(tick)}
            />
            <text
              className="fill-on-surface-variant"
              dominantBaseline="middle"
              fontSize="12"
              textAnchor="end"
              x={PADDING.left - 8}
              y={yPos(tick)}
            >
              {formatChartValue(tick, metric)}
            </text>
          </g>
        ))}

        <line
          className={style.stroke}
          strokeDasharray="7 6"
          strokeLinecap="round"
          strokeWidth="2"
          x1={PADDING.left}
          x2={chartWidth - PADDING.right}
          y1={yPos(averageValue)}
          y2={yPos(averageValue)}
        />
        <text
          className={style.fill}
          dominantBaseline="central"
          fontSize="12"
          fontWeight="700"
          x={chartWidth - PADDING.right + 8}
          y={yPos(averageValue)}
        >
          Avg {formatChartValue(averageValue, metric)}
        </text>

        <polyline
          className={`${style.stroke} fill-none`}
          points={points.map((point) => `${xPos(point.index)},${yPos(point.value)}`).join(" ")}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="3"
        />

        {points.map((point) => {
          const isBest = point === best;
          return (
            <g key={`dot-${point.index}`}>
              <circle
                className={`${style.stroke} ${isBest ? style.fill : "fill-background"}`}
                cx={xPos(point.index)}
                cy={yPos(point.value)}
                r={isBest ? 6 : 5}
                strokeWidth="3"
              />
              <text
                className="fill-on-surface"
                fontSize="12"
                fontWeight="700"
                textAnchor="middle"
                x={xPos(point.index)}
                y={yPos(point.value) - 12}
              >
                {formatChartValue(point.value, metric)}
              </text>
            </g>
          );
        })}

        {xLabels.map((point) => {
          const labelY = baseline + 16;
          return (
            <text
              key={`xlabel-${point.index}`}
              className="fill-on-surface-variant"
              dominantBaseline="hanging"
              fontSize="12"
              textAnchor="end"
              transform={`rotate(-35, ${xPos(point.index)}, ${labelY})`}
              x={xPos(point.index)}
              y={labelY}
            >
              {formatMMDDYYYY(point.date)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
