import type { PredictionRow } from "@/lib/data";

type FormatTop10TextOptions = {
  bandName: string;
  dateLabel: string;
  locationLabel: string;
  venueName: string;
  predictions: PredictionRow[];
  modelDisplayName: string;
  shareUrl: string;
};

export function formatTop10Text({
  bandName,
  dateLabel,
  locationLabel,
  venueName,
  predictions,
  shareUrl,
}: FormatTop10TextOptions): string {
  const top10 = predictions.slice(0, 10);

  const headerParts = [bandName, "Setlist Predictions"].join(" ");
  const sublabel = [venueName, locationLabel].filter(Boolean).join(" · ");
  const dateLine = [dateLabel, sublabel].filter(Boolean).join(" — ");

  const lines: string[] = [headerParts];

  if (dateLine) {
    lines.push(dateLine);
  }

  lines.push("");

  for (const row of top10) {
    lines.push(`${row.rank}. ${row.songName}`);
  }

  lines.push("");
  lines.push(shareUrl);

  return lines.join("\n");
}
