import type { AccuracyRow } from "@/lib/data";

type Props = {
  rows: AccuracyRow[];
};

function formatPercent(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

export function AccuracyTable({ rows }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-outline-variant/30">
      <table className="min-w-[720px] divide-y divide-outline-variant/30 text-left text-sm">
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Show Date</th>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Venue</th>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Top 10</th>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Top 25</th>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Top 50</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
          {rows.map((row, index) => (
            <tr key={`${row.showDate}-${index}`} className={index % 2 === 1 ? "bg-surface-container-low/40" : ""}>
              <td className="px-4 py-3">{row.showDate ?? "—"}</td>
              <td className="px-4 py-3 text-on-surface-variant">{row.venueName ?? "—"}</td>
              <td className="px-4 py-3 font-headline text-primary">{formatPercent(row.k10Recall)}</td>
              <td className="px-4 py-3">{formatPercent(row.k25Recall)}</td>
              <td className="px-4 py-3">{formatPercent(row.k50Recall)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
