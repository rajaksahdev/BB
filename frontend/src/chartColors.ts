/**
 * Stable palette for overlaid equity curves in the comparison view.
 * Tuned to stay bright and distinct on the dark terminal background.
 */
export const LINE_COLORS = ["#4f7cff", "#2fe08a", "#ffb020", "#ff5c7a"];

export function colorForIndex(i: number): string {
  return LINE_COLORS[i % LINE_COLORS.length];
}
