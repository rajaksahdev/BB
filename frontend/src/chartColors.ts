/**
 * Stable palette for overlaid equity curves in the comparison view.
 * Tuned to stay bright and distinct on the dark terminal background.
 */
export const LINE_COLORS = ["#4f7cff", "#2fe08a", "#ffb020", "#ff5c7a"];

export function colorForIndex(i: number): string {
  return LINE_COLORS[i % LINE_COLORS.length];
}

/**
 * Cell color scale for the optimizer heatmap.
 *
 * Signed metrics (the grid spans 0) get a diverging scale: red (loss) →
 * neutral gray at exactly 0 → blue (gain). Blue↔red is deliberate — it is far
 * safer under red-green colorblindness than the app's green/red P&L pair
 * (validated ΔE 20.6 vs 9.3), and exact values are always available in the
 * readout + ranked table so color never carries the number alone.
 * Single-signed metrics (win rate, drawdown) get a sequential neutral→blue
 * ramp where brighter always means better.
 */
const HEAT_NEUTRAL: Rgb = [58, 63, 77]; // desaturated slate, near --surface-3
const HEAT_POS: Rgb = [79, 124, 255]; // --accent blue
const HEAT_NEG: Rgb = [255, 92, 122]; // --neg red

type Rgb = [number, number, number];

function mix(a: Rgb, b: Rgb, t: number): string {
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * t));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

export function heatColor(value: number, min: number, max: number): string {
  if (min < 0 && max > 0) {
    // Diverging, anchored at zero so sign is never misread.
    const t = value / Math.max(Math.abs(min), Math.abs(max));
    return t >= 0 ? mix(HEAT_NEUTRAL, HEAT_POS, t) : mix(HEAT_NEUTRAL, HEAT_NEG, -t);
  }
  const span = max - min;
  const t = span > 0 ? (value - min) / span : 0.5;
  return mix(HEAT_NEUTRAL, HEAT_POS, t);
}
