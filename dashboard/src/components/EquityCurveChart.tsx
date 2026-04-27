"use client";

import { useEffect, useRef } from "react";
import { createChart, LineSeries, type IChartApi } from "lightweight-charts";

interface Props {
  data: number[];
  initialCapital: number;
  height?: number;
}

export default function EquityCurveChart({ data, initialCapital, height = 250 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: "#1a1b23" },
        textColor: "#71717a",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "#2a2b35" },
        horzLines: { color: "#2a2b35" },
      },
      rightPriceScale: {
        borderColor: "#2a2b35",
      },
      timeScale: {
        borderColor: "#2a2b35",
        visible: false,
      },
      crosshair: {
        mode: 0,
      },
    });

    chartRef.current = chart;

    const finalValue = data[data.length - 1];
    const lineColor = finalValue >= initialCapital ? "#22c55e" : "#ef4444";

    const lineSeries = chart.addSeries(LineSeries, {
      color: lineColor,
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });

    const lineData = data.map((value, i) => ({
      time: (i + 1) as unknown as number,
      value,
    }));

    lineSeries.setData(lineData as any);

    // Baseline at initial capital
    const baselineSeries = chart.addSeries(LineSeries, {
      color: "#71717a",
      lineWidth: 1,
      lineStyle: 2,
      crosshairMarkerVisible: false,
    });
    baselineSeries.setData([
      { time: 1 as any, value: initialCapital },
      { time: data.length as any, value: initialCapital },
    ]);

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, initialCapital, height]);

  return <div ref={containerRef} className="rounded-xl overflow-hidden border border-[var(--card-border)]" />;
}
