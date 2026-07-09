/**
 * Equity-curve chart (FR-04) built on lightweight-charts.
 *
 * Supports overlaying multiple runs so the comparison view (FR-08) can show
 * several equity curves on one set of axes.
 */

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { EquityPoint } from "../api";

export interface EquitySeries {
  label: string;
  color: string;
  points: EquityPoint[];
}

function toLineData(points: EquityPoint[]) {
  // lightweight-charts needs ascending, unique UNIX-second timestamps.
  return points.map((p) => ({
    time: Math.floor(Date.parse(p.time) / 1000) as UTCTimestamp,
    value: p.equity,
  }));
}

export default function EquityChart({ series }: { series: EquitySeries[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line">[]>([]);

  // Create the chart once; tear down on unmount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 360,
      layout: {
        // Dark trading-terminal theme, matching the app tokens.
        background: { type: ColorType.Solid, color: "#0c1119" },
        textColor: "#8b95a8",
        fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
      },
      grid: {
        vertLines: { color: "rgba(51, 65, 94, 0.35)" },
        horzLines: { color: "rgba(51, 65, 94, 0.35)" },
      },
      rightPriceScale: { borderColor: "#222c40" },
      timeScale: { borderColor: "#222c40", timeVisible: true },
      crosshair: {
        mode: 0,
        vertLine: { color: "rgba(79, 124, 255, 0.5)", labelBackgroundColor: "#4f7cff" },
        horzLine: { color: "rgba(79, 124, 255, 0.5)", labelBackgroundColor: "#4f7cff" },
      },
    });
    chartRef.current = chart;

    const handleResize = () => chart.applyOptions({ width: container.clientWidth });
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = [];
    };
  }, []);

  // Sync series whenever the data changes.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    // Drop old series, draw the current set.
    for (const s of seriesRef.current) chart.removeSeries(s);
    seriesRef.current = [];

    for (const s of series) {
      const line = chart.addLineSeries({
        color: s.color,
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: true,
        title: s.label,
      });
      line.setData(toLineData(s.points));
      seriesRef.current.push(line);
    }

    chart.timeScale().fitContent();
  }, [series]);

  return <div ref={containerRef} className="equity-chart" />;
}
