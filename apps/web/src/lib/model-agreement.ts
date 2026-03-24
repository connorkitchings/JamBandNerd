export type SongLike = {
  songName: string;
};

export type ModelAgreementTier = {
  matchCount: number;
  total: number;
  percentage: number;
};

export type ModelAgreement = {
  top10: ModelAgreementTier;
  top25: ModelAgreementTier;
  top50: ModelAgreementTier;
  composite: number;
};

export function calculateModelAgreement(
  primaryRows: SongLike[],
  secondaryRows: SongLike[],
): ModelAgreement | null {
  if (!primaryRows.length || !secondaryRows.length) return null;

  const primaryNames = primaryRows.map((row) => row.songName.toLowerCase());
  const secondaryNames = secondaryRows.map((row) => row.songName.toLowerCase());

  function computeTier(k: number): ModelAgreementTier {
    const primaryTopK = primaryNames.slice(0, k);
    const secondaryTopK = secondaryNames.slice(0, k);
    const secondaryTopKSet = new Set(secondaryTopK);
    const actualK = Math.min(k, primaryTopK.length, secondaryTopK.length);
    const matchCount = primaryTopK
      .slice(0, actualK)
      .filter((song) => secondaryTopKSet.has(song)).length;
    const percentage = actualK > 0 ? matchCount / actualK : 0;
    return { matchCount, total: actualK, percentage };
  }

  const top10 = computeTier(10);
  const top25 = computeTier(25);
  const top50 = computeTier(50);
  const maxWeight = top10.total * 2 + top25.total + top50.total;
  const composite =
    maxWeight > 0
      ? (top10.matchCount * 2 + top25.matchCount + top50.matchCount) / maxWeight
      : 0;

  return { top10, top25, top50, composite };
}
