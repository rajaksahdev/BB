/** Stable palette for overlaid equity curves in the comparison view. */
export const LINE_COLORS = ["#2962ff", "#e91e63", "#ff9800", "#26a69a"];

export function colorForIndex(i: number): string {
  return LINE_COLORS[i % LINE_COLORS.length];
}
