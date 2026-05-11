type PredictionUpdateScope = {
  band: string;
  targetShowKey?: string | null;
  targetShowDate?: string | null;
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
  const targetShowKey = readTextField(record, ["target_show_key", "targetShowKey"]);
  const targetShowDate = readTextField(record, [
    "target_show_date",
    "targetShowDate",
  ]);

  return (
    band === scope.band &&
    (
      Boolean(scope.targetShowKey && targetShowKey === scope.targetShowKey) ||
      Boolean(scope.targetShowDate && targetShowDate === scope.targetShowDate)
    )
  );
}
