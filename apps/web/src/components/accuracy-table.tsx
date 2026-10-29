import Link from "next/link";
import { Fragment } from "react";

import { bandPath } from "@/lib/band-routes";
import type { AccuracyRow } from "@/lib/data";
import { buildLocationLabel, formatHits, formatMMDDYYYY } from "@/lib/format";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_ROW_HEAD_CLASS,
} from "@/components/responsive-table";

type Props = {
  rows: AccuracyRow[];
  band?: string;
};

function formatPercent(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function stripLeadingThe(value: string | null) {
  if (!value) return null;
  return value.replace(/^The\s+/i, "");
}

const GROUPS = [
  { k: 10 as const, label: "Top 10", tone: "text-accent-text", hits: "p10" as const, cov: "recall10" as const },
  { k: 25 as const, label: "Top 25", tone: "text-teal", hits: "p25" as const, cov: "recall25" as const },
  { k: 50 as const, label: "Top 50", tone: "text-tier-top50", hits: "p50" as const, cov: "recall50" as const },
];

export function AccuracyTable({ rows, band }: Props) {
  return (
    <ResponsiveTableFrame
      caption="Prediction accuracy by show: hits and coverage for the top 10, 25 and 50 predicted songs"
      minWidthClassName="min-w-[860px]"
      testId="accuracy-table"
    >
      <thead className="bg-surface-2">
        <tr>
          <th scope="col" className={`${TABLE_HEAD_CLASS} whitespace-nowrap align-bottom`} rowSpan={2}>Show Date</th>
          <th scope="col" className={`${TABLE_HEAD_CLASS} align-bottom`} rowSpan={2}>Venue</th>
          <th scope="col" className={`${TABLE_HEAD_CLASS} align-bottom`} rowSpan={2}>Location</th>
          {GROUPS.map((group) => (
            <th
              key={group.k}
              scope="colgroup"
              colSpan={2}
              className={`${TABLE_HEAD_CLASS} text-center ${group.tone}`}
            >
              {group.label}
            </th>
          ))}
        </tr>
        <tr>
          {GROUPS.map((group) => (
            <Fragment key={group.k}>
              <th scope="col" className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center`}>Hits</th>
              <th scope="col" className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center`}>Coverage</th>
            </Fragment>
          ))}
        </tr>
      </thead>
      <tbody className="text-on-surface">
        {rows.map((row, index) => (
          <tr key={`${row.showDate}-${index}`}>
            <th scope="row" className={`${TABLE_ROW_HEAD_CLASS} whitespace-nowrap`}>
              {band && row.showDate ? (
                <Link
                  href={bandPath(band, "replay", row.showDate)}
                  className="inline-flex min-h-11 items-center underline underline-offset-4 hover:text-accent-text"
                >
                  {formatMMDDYYYY(row.showDate)}
                </Link>
              ) : (
                formatMMDDYYYY(row.showDate) ?? "—"
              )}
            </th>
            <td className={`${TABLE_CELL_CLASS} text-on-surface-variant`}>{stripLeadingThe(row.venueName) ?? "—"}</td>
            <td className={`${TABLE_CELL_CLASS} text-on-surface-variant`}>
              {buildLocationLabel([row.city, row.state]) || "—"}
            </td>
            {GROUPS.map((group) => (
              <Fragment key={group.k}>
                <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center`}>
                  {formatHits(row[group.hits], group.k)}
                </td>
                <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-center font-bold`}>
                  {formatPercent(row[group.cov])}
                </td>
              </Fragment>
            ))}
          </tr>
        ))}
      </tbody>
    </ResponsiveTableFrame>
  );
}
