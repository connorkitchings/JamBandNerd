import type { AccuracyRow } from "@/lib/data";
import { formatCompactDateLabel } from "@/lib/format";

type Props = {
  rows: AccuracyRow[];
  k?: 10 | 25 | 50 | "all";
};

const CHART_WIDTH = 800;
const CHART_HEIGHT = 240;
const PADDING = { top: 20, right: 20, bottom: 56, left: 48 };

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function getStrokeColor(k: 10 | 25 | 50) {
  return k === 10 ? "var(--color-primary)" : k === 25 ? "var(--color-tertiary)" : "#c084fc";
}

function buildPath(points: Array<{ index: number; value: number }>, plotWidth: number, plotHeight: number, yMin: number, yMax: number) {
  function xPos(index: number, totalPoints: number) {
    return PADDING.left + (index / Math.max(totalPoints - 1, 1)) * plotWidth;
  }

  function yPos(value: number) {
    return PADDING.top + plotHeight - ((clamp(value, yMin, yMax) - yMin) / (yMax - yMin)) * plotHeight;
  }

  return {
    linePath: (totalPoints: number) =>
      points
        .map((point, i) =>
          `${i === 0 ? "M" : "L"} ${xPos(point.index, totalPoints).toFixed(1)} ${yPos(point.value).toFixed(1)}`,
        )
        .join(" "),
    areaPath: (totalPoints: number) => {
      const linePath = points
        .map((point, i) =>
          `${i === 0 ? "M" : "L"} ${xPos(point.index, totalPoints).toFixed(1)} ${yPos(point.value).toFixed(1)}`,
        )
        .join(" ");
      return `${linePath} L ${xPos(points[points.length - 1]?.index ?? 0, totalPoints).toFixed(1)} ${(PADDING.top + plotHeight).toFixed(1)} L ${xPos(points[0]?.index ?? 0, totalPoints).toFixed(1)} ${(PADDING.top + plotHeight).toFixed(1)} Z`;
    },
    xPos,
    yPos,
  };
}

export function RecallChart({ rows, k = 10 }: Props) {
  const chronological = [...rows].reverse();
  const totalRows = chronological.length;
  const seriesEntries = [
    { key: 10 as const, label: "Top 10", color: getStrokeColor(10), values: chronological.map((row, index) => ({ index, date: row.showDate, value: row.k10Recall })) },
    { key: 25 as const, label: "Top 25", color: getStrokeColor(25), values: chronological.map((row, index) => ({ index, date: row.showDate, value: row.k25Recall })) },
    { key: 50 as const, label: "Top 50", color: getStrokeColor(50), values: chronological.map((row, index) => ({ index, date: row.showDate, value: row.k50Recall })) },
  ] as const;

  const visibleSeries = (k === "all" ? seriesEntries : seriesEntries.filter((entry) => entry.key === k))
    .map((entry) => ({
      ...entry,
      points: entry.values.filter(
        (point): point is { index: number; date: string | null; value: number } => point.value !== null,
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

  const maxValue = Math.max(...visibleSeries.flatMap((series) => series.points.map((point) => point.value)));
  const yMin = 0;
  const yMax = Math.min(1, Math.ceil(maxValue * 10) / 10 + 0.1);

  const yTicks: number[] = [];
  for (let v = 0; v <= yMax; v += 0.1) {
    yTicks.push(Math.round(v * 100) / 100);
  }

  const labelInterval = Math.max(1, Math.floor(totalRows / 6));
  const xLabels = chronological
    .map((row, index) => ({ index, date: row.showDate }))
    .filter((_, i) => i % labelInterval === 0 || i === totalRows - 1);
  const xPos = (index: number) =>
    PADDING.left + (index / Math.max(totalRows - 1, 1)) * plotWidth;
  const yPos = (value: number) =>
    PADDING.top + plotHeight - ((clamp(value, yMin, yMax) - yMin) / (yMax - yMin)) * plotHeight;

  return (
    <div className="w-full overflow-x-auto">
      {k === "all" ? (
        <div className="mb-4 flex flex-wrap gap-3">
          {visibleSeries.map((series) => (
            <div
              key={series.key}
              className="inline-flex items-center gap-2 rounded-full border border-outline-variant/20 bg-surface-container-low px-3 py-1.5"
            >
              <span
                aria-hidden="true"
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: series.color }}
              />
              <span className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                {series.label}
              </span>
            </div>
          ))}
        </div>
      ) : null}
      <svg
        aria-label={k === "all" ? "Accuracy over time for Top 10, Top 25, and Top 50" : `Top-${k} accuracy over time`}
        className="h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      >
        <defs>
          {visibleSeries.map((series) => (
            <linearGradient
              id={`recall-fill-gradient-${series.key}`}
              key={`gradient-${series.key}`}
              x1="0"
              x2="0"
              y1="0"
              y2="1"
            >
              <stop offset="0%" stopColor={series.color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={series.color} stopOpacity="0.02" />
            </linearGradient>
          ))}
        </defs>

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
              {`${Math.round(tick * 100)}%`}
            </text>
          </g>
        ))}

        {visibleSeries.map((series) => {
          const pathTools = buildPath(series.points, plotWidth, plotHeight, yMin, yMax);
          const linePath = pathTools.linePath(totalRows);
          const areaPath = pathTools.areaPath(totalRows);
          return (
            <g key={`series-${series.key}`}>
              {k !== "all" ? (
                <path d={areaPath} fill={`url(#recall-fill-gradient-${series.key})`} />
              ) : null}
              <path
                d={linePath}
                fill="none"
                stroke={series.color}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={k === "all" ? 2 : 2.5}
              />
              {series.points.map((point, index) => (
                <g key={`dot-${series.key}-${index}`}>
                  <circle
                    cx={pathTools.xPos(point.index, totalRows)}
                    cy={pathTools.yPos(point.value)}
                    fill="var(--color-surface-container)"
                    r={k === "all" ? 4 : 5}
                    stroke={series.color}
                    strokeWidth="2"
                  />
                  {k !== "all" && (series.points.length <= 8 || index % 2 === 0) ? (
                    <text
                      dominantBaseline="auto"
                      fill="var(--color-on-surface)"
                      fontSize="9"
                      fontWeight="600"
                      textAnchor="middle"
                      x={pathTools.xPos(point.index, totalRows)}
                      y={pathTools.yPos(point.value) - 10}
                    >
                      {`${Math.round(point.value * 100)}%`}
                    </text>
                  ) : null}
                </g>
              ))}
            </g>
          );
        })}

        {xLabels.map((point) => {
          return (
            <text
              key={`xlabel-${point.index}`}
              dominantBaseline="hanging"
              fill="var(--color-on-surface-variant)"
              fontSize="9"
              textAnchor={point.index === 0 ? "start" : point.index === totalRows - 1 ? "end" : "middle"}
              transform={`rotate(-30, ${xPos(point.index)}, ${PADDING.top + plotHeight + 12})`}
              x={xPos(point.index)}
              y={PADDING.top + plotHeight + 12}
            >
              {formatCompactDateLabel(point.date)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
