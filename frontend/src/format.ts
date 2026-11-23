export function formatPercent(value: number): string {
  if (value > 0 && value < 1) return "< 1 %";
  return `${Math.round(value)} %`;
}

export function formatCount(value: number): string {
  return value.toFixed(2);
}
