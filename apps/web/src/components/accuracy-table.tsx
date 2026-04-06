import Link from "next/link";

import type { BandSlug } from "@/lib/config";
import type { AccuracyRow } from "@/lib/data";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
} from "@/components/responsive-table";

type Props = {
  rows: AccuracyRow[];
  replayBand?: BandSlug;
};

function formatPercent(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

export function AccuracyTable({ rows, replayBand }: Props) {
  return (
    <ResponsiveTableFrame
      minWidthClassName="min-w-[820px] divide-y divide-outline-variant/30"
      testId="accuracy-table"
    >
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Show Date</th>
            <th className={TABLE_HEAD_CLASS}>Venue</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Top 10</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Top 25</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Top 50</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-right`}></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
          {rows.map((row, index) => (
            <tr key={`${row.showDate}-${index}`} className={index % 2 === 1 ? "bg-surface-container-low/40" : ""}>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>{row.showDate ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} text-on-surface-variant`}>{row.venueName ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap font-headline tabular-nums text-primary`}>
                {formatPercent(row.k10Recall)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap tabular-nums`}>
                {formatPercent(row.k25Recall)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap tabular-nums`}>
                {formatPercent(row.k50Recall)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-right`}>
                {replayBand && row.showDate ? (
                  <Link
                    href={`/replay?band=${replayBand}&date=${row.showDate}`}
                    className="inline-flex items-center justify-center rounded-full border border-outline-variant/30 bg-surface/70 px-3 py-1.5 font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
                  >
                    Replay
                  </Link>
                ) : (
                  <span className="text-on-surface-variant">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
    </ResponsiveTableFrame>
  );
}
