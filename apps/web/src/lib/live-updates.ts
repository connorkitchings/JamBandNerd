type PredictionUpdateScope = {
  band: string;
  model: string;
  referenceDate: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function readTextField(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string") {
      return value;
    }
  }

  return null;
}

export function matchesPredictionUpdateScope(
  payloadRecord: unknown,
  scope: PredictionUpdateScope,
) {
  const record = asRecord(payloadRecord);
  if (!record) {
    return false;
  }

  const band = readTextField(record, ["band"]);
  const model = readTextField(record, ["model_slug", "modelSlug", "model"]);
  const referenceDate = readTextField(record, ["reference_date", "referenceDate"]);

  return (
    band === scope.band &&
    model === scope.model &&
    referenceDate === scope.referenceDate
  );
}
