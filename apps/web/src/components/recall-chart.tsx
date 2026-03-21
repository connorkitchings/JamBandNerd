import type { AccuracyRow } from "@/lib/data";
import { formatCompactDateLabel } from "@/lib/format";

type Props = {
  rows: AccuracyRow[];
};

const CHART_WIDTH = 800;
const CHART_HEIGHT = 240;
const PADDING = { top: 20, right: 20, bottom: 56, left: 48 };

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function RecallChart({ rows }: Props) {
  // Reverse so chronological order is left→right
  const chronological = [...rows].reverse();
  const points = chronological
    .map((row, index) => ({
      index,
      date: row.showDate,
      value: row.k10Recall,
    }))
    .filter((point): point is { index: number; date: string | null; value: number } =>
      point.value !== null,
    );

  if (points.length < 2) {
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

  // Y-axis scale: 0% to max value rounded up to nearest 10%
  const maxValue = Math.max(...points.map((p) => p.value));
  const yMax = Math.min(1, Math.ceil(maxValue * 10) / 10 + 0.1);
  const yMin = 0;

  function xPos(i: number) {
    return PADDING.left + (i / (points.length - 1)) * plotWidth;
  }

  function yPos(value: number) {
    return PADDING.top + plotHeight - ((clamp(value, yMin, yMax) - yMin) / (yMax - yMin)) * plotHeight;
  }

  // Build the line path
  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xPos(i).toFixed(1)} ${yPos(p.value).toFixed(1)}`)
    .join(" ");

  // Build the area fill path
  const areaPath = `${linePath} L ${xPos(points.length - 1).toFixed(1)} ${(PADDING.top + plotHeight).toFixed(1)} L ${xPos(0).toFixed(1)} ${(PADDING.top + plotHeight).toFixed(1)} Z`;

  // Y-axis gridlines
  const yTicks: number[] = [];
  for (let v = 0; v <= yMax; v += 0.1) {
    yTicks.push(Math.round(v * 100) / 100);
  }

  // X-axis labels: show ~6 labels max
  const labelInterval = Math.max(1, Math.floor(points.length / 6));
  const xLabels = points.filter((_, i) => i % labelInterval === 0 || i === points.length - 1);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        aria-label="Top-10 recall over time"
        className="h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      >
        <defs>
          <linearGradient id="recall-fill-gradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Gridlines */}
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

        {/* Area fill */}
        <path d={areaPath} fill="url(#recall-fill-gradient)" />

        {/* Line */}
        <path
          d={linePath}
          fill="none"
          stroke="var(--color-primary)"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2.5"
        />

        {/* Data points */}
        {points.map((point, i) => (
          <g key={`dot-${i}`}>
            <circle
              cx={xPos(i)}
              cy={yPos(point.value)}
              fill="var(--color-surface-container)"
              r="5"
              stroke="var(--color-primary)"
              strokeWidth="2"
            />
            {/* Show value label on every other point or if few points */}
            {(points.length <= 8 || i % 2 === 0) && (
              <text
                dominantBaseline="auto"
                fill="var(--color-on-surface)"
                fontSize="9"
                fontWeight="600"
                textAnchor="middle"
                x={xPos(i)}
                y={yPos(point.value) - 10}
              >
                {`${Math.round(point.value * 100)}%`}
              </text>
            )}
          </g>
        ))}

        {/* X-axis labels */}
        {xLabels.map((point) => {
          const originalIndex = points.indexOf(point);
          return (
            <text
              key={`xlabel-${originalIndex}`}
              dominantBaseline="hanging"
              fill="var(--color-on-surface-variant)"
              fontSize="9"
              textAnchor="middle"
              transform={`rotate(-30, ${xPos(originalIndex)}, ${PADDING.top + plotHeight + 12})`}
              x={xPos(originalIndex)}
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
