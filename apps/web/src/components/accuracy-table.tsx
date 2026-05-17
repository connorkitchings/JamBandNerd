import type { AccuracyRow } from "@/lib/data";
import { formatAvgHits } from "@/lib/format";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
} from "@/components/responsive-table";

type Props = {
  rows: AccuracyRow[];
};

function formatPercent(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

export function AccuracyTable({ rows }: Props) {
  return (
    <div>
      <p className="mb-3 text-xs leading-5 text-on-surface-variant">
        C = coverage (share of setlist caught). H = avg. hits (picks played out of the Top-X group).
      </p>
      <ResponsiveTableFrame
        minWidthClassName="min-w-[820px] divide-y divide-outline-variant/30"
        testId="accuracy-table"
      >
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Show Date</th>
            <th className={TABLE_HEAD_CLASS}>Venue</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>C10</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>H10</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>C25</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>H25</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>C50</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>H50</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
          {rows.map((row, index) => (
            <tr key={`${row.showDate}-${index}`} className={index % 2 === 1 ? "bg-surface-container-low/40" : ""}>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>{row.showDate ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} text-on-surface-variant`}>{row.venueName ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap font-headline tabular-nums text-primary`}>
                {formatPercent(row.recall10)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap tabular-nums`}>
                {formatAvgHits(row.p10, 10)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap font-headline tabular-nums text-primary`}>
                {formatPercent(row.recall25)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap tabular-nums`}>
                {formatAvgHits(row.p25, 25)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap font-headline tabular-nums text-primary`}>
                {formatPercent(row.recall50)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap tabular-nums`}>
                {formatAvgHits(row.p50, 50)}
              </td>
            </tr>
          ))}
        </tbody>
      </ResponsiveTableFrame>
    </div>
  );
}
