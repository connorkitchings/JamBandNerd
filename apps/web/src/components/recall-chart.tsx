import type { AccuracyRow } from "@/lib/data";
import { formatMMDDYYYY } from "@/lib/format";
import type { ChartMetric } from "@/components/chart-metric-toggle";

type Props = {
  rows: AccuracyRow[];
  k?: 10 | 25 | 50;
  metric?: ChartMetric;
};

const CHART_WIDTH = 760;
const CHART_HEIGHT = 340;
const PADDING = { top: 28, right: 76, bottom: 86, left: 48 };
const MAX_X_AXIS_LABELS = 6;
const X_AXIS_LABEL_OFFSET = 28;

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function getStrokeColor(k: 10 | 25 | 50) {
  return k === 10 ? "var(--color-primary)" : k === 25 ? "var(--color-tertiary)" : "var(--color-tier-top50)";
}

function formatChartValue(value: number, metric: ChartMetric) {
  return metric === "coverage"
    ? `${Math.round(value * 100)}%`
    : String(Math.round(value));
}

function averageChartValue(points: Array<{ value: number }>) {
  return points.reduce((sum, point) => sum + point.value, 0) / points.length;
}

export function RecallChart({ rows, k = 10, metric = "coverage" }: Props) {
  const chronological = [...rows].reverse();
  const totalRows = chronological.length;
  const top10Values: Array<{
    index: number;
    date: string | null;
    venueName: string | null;
    value: number | null;
  }> = [];
  const top25Values: Array<{
    index: number;
    date: string | null;
    venueName: string | null;
    value: number | null;
  }> = [];
  const top50Values: Array<{
    index: number;
    date: string | null;
    venueName: string | null;
    value: number | null;
  }> = [];

  chronological.forEach((row, index) => {
    top10Values.push({
      index,
      date: row.showDate,
      venueName: row.venueName,
      value: metric === "coverage" ? row.recall10 : row.p10 === null ? null : row.p10 * 10,
    });
    top25Values.push({
      index,
      date: row.showDate,
      venueName: row.venueName,
      value: metric === "coverage" ? row.recall25 : row.p25 === null ? null : row.p25 * 25,
    });
    top50Values.push({
      index,
      date: row.showDate,
      venueName: row.venueName,
      value: metric === "coverage" ? row.recall50 : row.p50 === null ? null : row.p50 * 50,
    });
  });

  const seriesEntries = [
    { key: 10 as const, label: "Top 10", color: getStrokeColor(10), values: top10Values },
    { key: 25 as const, label: "Top 25", color: getStrokeColor(25), values: top25Values },
    { key: 50 as const, label: "Top 50", color: getStrokeColor(50), values: top50Values },
  ] as const;

  const visibleSeries = seriesEntries
    .filter((entry) => entry.key === k)
    .map((entry) => ({
      ...entry,
      points: entry.values.filter(
        (point): point is {
          index: number;
          date: string | null;
          venueName: string | null;
          value: number;
        } => point.value !== null,
      ),
    }))
    .filter((entry) => entry.points.length >= 2);

  if (visibleSeries.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-outline-variant/20 bg-surface-container-low">
        <p className="text-sm text-on-surface-variant">
          Need at least two scored shows to render a chart.
        </p>
      </div>
    );
  }

  const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;

  const yMin = 0;
  const yMax =
    metric === "coverage"
      ? 1
      : k === 10
        ? 10
        : k === 25
          ? 15
          : 20;

  const yTicks: number[] = [];
  const tickStep = metric === "coverage" ? 0.1 : Math.max(1, Math.ceil(yMax / 5));
  for (let v = 0; v <= yMax; v += tickStep) {
    yTicks.push(metric === "coverage" ? Math.round(v * 100) / 100 : v);
  }

  const labelInterval =
    totalRows <= 1
      ? 1
      : Math.max(1, Math.ceil((totalRows - 1) / Math.max(MAX_X_AXIS_LABELS - 1, 1)));
  const xLabels = chronological
    .map((row, index) => ({ index, date: row.showDate }))
    .filter((_, i) => i % labelInterval === 0 || i === totalRows - 1);
  const xPos = (index: number) =>
    PADDING.left + (index / Math.max(totalRows - 1, 1)) * plotWidth;
  const yPos = (value: number) =>
    PADDING.top + plotHeight - ((clamp(value, yMin, yMax) - yMin) / (yMax - yMin)) * plotHeight;

  return (
    <div className="mx-auto w-full max-w-[960px] overflow-hidden pb-2">
      <svg
        aria-label={`Show-by-show Top-${k} ${metric === "coverage" ? "coverage" : "hits"}`}
        className="h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      >
        {yTicks.map((tick) => (
          <g key={`grid-${tick}`}>
            <line
              stroke="var(--color-outline-variant)"
              strokeDasharray="4 4"
              strokeOpacity="0.2"
              x1={PADDING.left}
              x2={CHART_WIDTH - PADDING.right}
              y1={yPos(tick)}
              y2={yPos(tick)}
            />
            <text
              dominantBaseline="middle"
              fill="var(--color-on-surface-variant)"
              fontSize="10"
              textAnchor="end"
              x={PADDING.left - 8}
              y={yPos(tick)}
            >
              {formatChartValue(tick, metric)}
            </text>
          </g>
        ))}

        {visibleSeries.map((series) => {
          const averageValue = averageChartValue(series.points);
          const averageY = yPos(averageValue);

          return (
            <g key={`series-${series.key}`}>
              <line
                stroke={series.color}
                strokeDasharray="7 6"
                strokeLinecap="round"
                strokeOpacity="0.9"
                strokeWidth="2.5"
                x1={PADDING.left}
                x2={CHART_WIDTH - PADDING.right}
                y1={averageY}
                y2={averageY}
              />
              <text
                dominantBaseline="central"
                fill={series.color}
                fontSize="10"
                fontWeight="700"
                textAnchor="start"
                x={CHART_WIDTH - PADDING.right + 8}
                y={averageY}
              >
                Avg {formatChartValue(averageValue, metric)}
              </text>
              {series.points.map((point, index) => (
                <g key={`dot-${series.key}-${index}`}>
                  <circle
                    cx={xPos(point.index)}
                    cy={yPos(point.value)}
                    fill="var(--color-surface-container)"
                    r="5"
                    stroke={series.color}
                    strokeWidth="2"
                  />
                </g>
              ))}
            </g>
          );
        })}

        <line
          stroke="var(--color-outline-variant)"
          strokeOpacity="0.35"
          x1={PADDING.left}
          x2={CHART_WIDTH - PADDING.right}
          y1={PADDING.top + plotHeight}
          y2={PADDING.top + plotHeight}
        />

        {xLabels.map((point) => {
          const labelY = PADDING.top + plotHeight + X_AXIS_LABEL_OFFSET;
          return (
            <text
              key={`xlabel-${point.index}`}
              dominantBaseline="hanging"
              fill="var(--color-on-surface-variant)"
              fontSize="9"
              textAnchor={point.index === 0 ? "start" : point.index === totalRows - 1 ? "end" : "middle"}
              transform={`rotate(-30, ${xPos(point.index)}, ${labelY})`}
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
