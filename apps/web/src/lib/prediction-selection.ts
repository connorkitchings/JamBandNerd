export type PredictionSeedRow = {
  reference_date: string | null;
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
    (row) => Boolean(row.reference_date) && Boolean(row.model_version),
  );

  if (validRows.length === 0) {
    return null;
  }

  const futureRows = validRows
    .filter((row) => (row.reference_date ?? "") >= todayIso)
    .toSorted((left, right) => {
      const refComparison = compareNullableStringsAsc(
        left.reference_date,
        right.reference_date,
      );
      if (refComparison !== 0) {
        return refComparison;
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

      return compareNullableStringsDesc(left.reference_date, right.reference_date);
    })[0] ?? null
  );
}
