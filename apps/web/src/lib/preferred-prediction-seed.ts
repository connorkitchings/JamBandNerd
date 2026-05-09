export type PredictionSeedRow = {
  target_show_date: string;
  reference_date: string;
  generated_at: string;
  model_version: string;
};

export function selectPreferredPredictionSeed(
  rows: PredictionSeedRow[],
  options: { todayIso: string },
): PredictionSeedRow | null {
  const { todayIso } = options;

  const futureRows = rows.filter((row) => row.target_show_date >= todayIso);

  if (futureRows.length > 0) {
    return futureRows.toSorted((left, right) => {
      const targetComparison = left.target_show_date.localeCompare(
        right.target_show_date,
      );
      if (targetComparison !== 0) {
        return targetComparison;
      }
      return right.generated_at.localeCompare(left.generated_at);
    })[0] ?? null;
  }

  return rows.toSorted((left, right) => {
    const generatedComparison = right.generated_at.localeCompare(
      left.generated_at,
    );
    if (generatedComparison !== 0) {
      return generatedComparison;
    }
    return right.target_show_date.localeCompare(left.target_show_date);
  })[0] ?? null;
}
