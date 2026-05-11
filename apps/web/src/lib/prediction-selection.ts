export type PredictionSeedRow = {
  reference_date: string | null;
  target_show_date: string | null;
  target_show_key: string | null;
  predicted_at: string | null;
  model_version: string | null;
};

function compareNullableStringsAsc(left: string | null, right: string | null): number {
  return (left ?? "").localeCompare(right ?? "");
}

function compareNullableStringsDesc(left: string | null, right: string | null): number {
  return compareNullableStringsAsc(right, left);
}

export function selectLivePredictionSeedRow(
  rows: PredictionSeedRow[],
  options: { todayIso: string },
): PredictionSeedRow | null {
  const { todayIso } = options;
  const validRows = rows.filter(
    (row) =>
      Boolean(row.target_show_date) &&
      Boolean(row.target_show_key) &&
      Boolean(row.model_version),
  );

  if (validRows.length === 0) {
    return null;
  }

  const futureRows = validRows
    .filter((row) => (row.target_show_date ?? "") >= todayIso)
    .toSorted((left, right) => {
      const targetComparison = compareNullableStringsAsc(
        left.target_show_date,
        right.target_show_date,
      );
      if (targetComparison !== 0) {
        return targetComparison;
      }

      return compareNullableStringsDesc(left.predicted_at, right.predicted_at);
    });

  if (futureRows.length > 0) {
    return futureRows[0] ?? null;
  }

  return (
    validRows.toSorted((left, right) => {
      const predictedComparison = compareNullableStringsDesc(
        left.predicted_at,
        right.predicted_at,
      );
      if (predictedComparison !== 0) {
        return predictedComparison;
      }

      return compareNullableStringsDesc(
        left.target_show_date,
        right.target_show_date,
      );
    })[0] ?? null
  );
}
