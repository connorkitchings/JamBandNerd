import Link from "next/link";

import type { AccuracyRow } from "@/lib/data";
import { formatHits } from "@/lib/format";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
} from "@/components/responsive-table";

type Props = {
  rows: AccuracyRow[];
  band?: string;
};

function formatPercent(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

export function AccuracyTable({ rows, band }: Props) {
  return (
    <div>
      <ResponsiveTableFrame
        minWidthClassName="min-w-[820px] divide-y divide-outline-variant/30"
        testId="accuracy-table"
      >
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap align-bottom`} rowSpan={2}>Show Date</th>
            <th className={`${TABLE_HEAD_CLASS} align-bottom`} rowSpan={2}>Venue</th>
            <th
              className={`${TABLE_HEAD_CLASS} border-b border-primary/25 text-center text-primary`}
              colSpan={2}
            >
              Top 10
            </th>
            <th
              className={`${TABLE_HEAD_CLASS} border-b border-tertiary/25 text-center text-tertiary`}
              colSpan={2}
            >
              Top 25
            </th>
            <th
              className={`${TABLE_HEAD_CLASS} border-b border-tier-top50/25 text-center text-tier-top50`}
              colSpan={2}
            >
              Top 50
            </th>
          </tr>
          <tr>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center text-tertiary`}>Hits</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center text-primary`}>Cov</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center text-tertiary`}>Hits</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center text-primary`}>Cov</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center text-tertiary`}>Hits</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center text-primary`}>Cov</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
          {rows.map((row, index) => (
            <tr key={`${row.showDate}-${index}`} className={index % 2 === 1 ? "bg-surface-container-low/40" : ""}>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>
                {band && row.showDate ? (
                  <Link
                    href={`/replay?band=${encodeURIComponent(band)}&date=${encodeURIComponent(row.showDate)}`}
                    className="text-on-surface underline-offset-4 hover:text-primary hover:underline focus-visible:text-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
                  >
                    {row.showDate}
                  </Link>
                ) : (
                  row.showDate ?? "—"
                )}
              </td>
              <td className={`${TABLE_CELL_CLASS} text-on-surface-variant`}>{row.venueName ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center tabular-nums text-tertiary`}>
                {formatHits(row.p10, 10)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center font-headline tabular-nums text-primary`}>
                {formatPercent(row.recall10)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center tabular-nums text-tertiary`}>
                {formatHits(row.p25, 25)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center font-headline tabular-nums text-primary`}>
                {formatPercent(row.recall25)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center tabular-nums text-tertiary`}>
                {formatHits(row.p50, 50)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center font-headline tabular-nums text-primary`}>
                {formatPercent(row.recall50)}
              </td>
            </tr>
          ))}
        </tbody>
      </ResponsiveTableFrame>
    </div>
  );
}
