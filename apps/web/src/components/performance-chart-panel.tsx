"use client";

import { useEffect, useState } from "react";

import { ChartMetricToggle, type ChartMetric } from "@/components/chart-metric-toggle";
import { KToggle, type KSelection } from "@/components/k-toggle";
import { RecallChart } from "@/components/recall-chart";
import type { AccuracyRow } from "@/lib/data";

type Props = {
  rows: AccuracyRow[];
};

function parseK(value: string | null): KSelection {
  return value === "25" ? 25 : value === "50" ? 50 : 10;
}

function parseMetric(value: string | null): ChartMetric {
  return value === "hits" ? "hits" : "coverage";
}

/**
 * Accuracy chart with its K and measure toggles.
 *
 * The selection is client state, so changing it never triggers a server render.
 * It is seeded from `?k=&metric=` after mount and mirrored back with
 * `history.replaceState`, which keeps the URL shareable.
 */
export function PerformanceChartPanel({ rows }: Props) {
  const [k, setK] = useState<KSelection>(10);
  const [metric, setMetric] = useState<ChartMetric>("coverage");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    // Seeding from the URL must wait for mount to keep server and client markup identical.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setK(parseK(params.get("k")));
    setMetric(parseMetric(params.get("metric")));
  }, []);

  function updateUrl(key: "k" | "metric", value: string) {
    const params = new URLSearchParams(window.location.search);
    params.set(key, value);
    window.history.replaceState(null, "", `?${params}`);
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-3 min-[430px]:grid-cols-2 md:flex md:flex-wrap md:items-end md:gap-6">
        <div className="space-y-1.5">
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
            Measure
          </p>
          <ChartMetricToggle
            currentMetric={metric}
            onChange={(next) => {
              setMetric(next);
              updateUrl("metric", next);
            }}
          />
        </div>
        <div className="space-y-1.5">
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
            Prediction Group
          </p>
          <KToggle
            currentK={k}
            onChange={(next) => {
              setK(next);
              updateUrl("k", String(next));
            }}
          />
        </div>
      </div>
      <RecallChart rows={rows} k={k} metric={metric} />
    </div>
  );
}
