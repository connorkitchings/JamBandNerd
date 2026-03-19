import type { PredictionRow } from "@/lib/data";

type Props = {
  rows: PredictionRow[];
  mode: "notebook" | "ckplus";
};

function renderNumber(value: number | null, digits = 0) {
  return value === null ? "—" : value.toFixed(digits);
}

function getSignalPercent(row: PredictionRow, mode: "notebook" | "ckplus", maxValue: number) {
  if (row.probability !== null) {
    return Math.round(Math.max(0, Math.min(1, row.probability)) * 100);
  }

  if (mode === "notebook") {
    const baseline = row.playsPastYear ?? row.rank;
    return Math.max(12, Math.round((baseline / maxValue) * 100));
  }

  const baseline = row.ckplusScore ?? row.gapRatio ?? row.rank;
  return Math.max(12, Math.round((baseline / maxValue) * 100));
}

function getTypeChip(row: PredictionRow) {
  if ((row.currentGap ?? 0) >= 20) {
    return {
      label: "Bust-Out",
      className: "border-tertiary/20 text-tertiary",
      subtitle: "Bust-out potential",
    };
  }

  if (row.rank <= 2) {
    return {
      label: "High Confidence",
      className: "border-primary/20 text-primary",
      subtitle: "Primary rotation",
    };
  }

  if ((row.currentGap ?? 0) <= 5) {
    return {
      label: "New Slot",
      className: "border-primary/20 text-primary",
      subtitle: "Recent activity",
    };
  }

  return {
    label: "Recurring",
    className: "border-primary/20 text-primary",
    subtitle: "Standard",
  };
}

export function PredictionTable({ rows, mode }: Props) {
  const limitedRows = rows.slice(0, 10);
  const maxValue = Math.max(
    1,
    ...limitedRows.map((row) =>
      mode === "notebook"
        ? row.playsPastYear ?? 0
        : row.ckplusScore ?? row.gapRatio ?? 0,
    ),
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[880px] border-collapse text-left">
        <thead>
          <tr>
            <th className="px-4 py-4 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Rank
            </th>
            <th className="px-4 py-4 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Song Title
            </th>
            <th className="px-4 py-4 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Last Played
            </th>
            <th className="px-4 py-4 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Gap
            </th>
            <th className="px-4 py-4 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Confidence
            </th>
            <th className="px-4 py-4 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Type
            </th>
          </tr>
        </thead>
        <tbody>
          {limitedRows.map((row, index) => {
            const signalPercent = getSignalPercent(row, mode, maxValue);
            const chip = getTypeChip(row);

            return (
              <tr
                key={`${row.rank}-${row.songName}`}
                className={`group transition-colors hover:bg-surface-container-low ${
                  index % 2 === 1 ? "bg-surface-container-low/30" : ""
                }`}
              >
                <td className="px-4 py-5 font-headline text-lg font-bold text-primary">
                  {String(row.rank).padStart(2, "0")}
                </td>
                <td className="px-4 py-5">
                  <div className="flex flex-col">
                    <span className="font-headline font-bold text-on-surface">{row.songName}</span>
                    <span className="font-label text-[10px] uppercase text-on-surface-variant">
                      {chip.subtitle}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-5 text-sm text-on-surface-variant">
                  {row.lastPlayed ?? "Unknown"}
                </td>
                <td className="px-4 py-5 font-headline text-sm">
                  {renderNumber(row.currentGap)} {row.currentGap === 1 ? "Show" : "Shows"}
                </td>
                <td className="px-4 py-5">
                  <div className="h-1.5 w-full max-w-[100px] rounded-full bg-surface-container-highest">
                    <div
                      className={`h-full rounded-full ${
                        chip.label === "Bust-Out" ? "bg-tertiary" : "bg-primary"
                      }`}
                      style={{ width: `${signalPercent}%` }}
                    />
                  </div>
                  <span
                    className={`mt-1 inline-block font-label text-[10px] ${
                      chip.label === "Bust-Out" ? "text-tertiary" : "text-primary"
                    }`}
                  >
                    {signalPercent.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-5">
                  <span
                    className={`px-2 py-0.5 font-label text-[9px] uppercase ${chip.className} border`}
                  >
                    {chip.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
