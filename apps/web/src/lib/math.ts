export function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value !== null);
  if (filtered.length === 0) {
    return null;
  }
  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}
