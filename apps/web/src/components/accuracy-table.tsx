import type { AccuracyRow } from "@/lib/data";
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
    <ResponsiveTableFrame
      minWidthClassName="min-w-[720px] divide-y divide-outline-variant/30"
      testId="accuracy-table"
    >
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Show Date</th>
            <th className={TABLE_HEAD_CLASS}>Venue</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Top 10</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Top 25</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Top 50</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
          {rows.map((row, index) => (
            <tr key={`${row.showDate}-${index}`} className={index % 2 === 1 ? "bg-surface-container-low/40" : ""}>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>{row.showDate ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} text-on-surface-variant`}>{row.venueName ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap font-headline text-primary`}>
                {formatPercent(row.k10Recall)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>
                {formatPercent(row.k25Recall)}
              </td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>
                {formatPercent(row.k50Recall)}
              </td>
            </tr>
          ))}
        </tbody>
    </ResponsiveTableFrame>
  );
}
