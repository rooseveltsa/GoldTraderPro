"use client";

import { useEffect, useRef } from "react";
import { createChart, createSeriesMarkers, CandlestickSeries, HistogramSeries, type IChartApi } from "lightweight-charts";
import type { CandleData } from "@/lib/api";

interface SignalMarker {
  time: string;
  direction: "BULLISH" | "BEARISH";
  pattern: string;
  price: number;
}

interface Props {
  candles: CandleData[];
  height?: number;
  signals?: SignalMarker[];
}

export default function CandlestickChart({ candles, height = 500, signals = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    // Limpar chart anterior
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
      crosshair: {
        mode: 0,
      },
      timeScale: {
        borderColor: "#2a2b35",
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: "#2a2b35",
      },
    });

    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const data = candles.map((c) => ({
      time: (new Date(c.timestamp).getTime() / 1000) as number,
      open: parseFloat(c.open),
      high: parseFloat(c.high),
      low: parseFloat(c.low),
      close: parseFloat(c.close),
    }));

    candleSeries.setData(data as any);

    // Signal markers (lightweight-charts v5 plugin API)
    if (signals.length > 0) {
      const markers = signals.map((s) => ({
        time: (new Date(s.time).getTime() / 1000) as number,
        position: s.direction === "BULLISH" ? ("belowBar" as const) : ("aboveBar" as const),
        color: s.direction === "BULLISH" ? "#22c55e" : "#ef4444",
        shape: s.direction === "BULLISH" ? ("arrowUp" as const) : ("arrowDown" as const),
        text: s.pattern,
      }));
      createSeriesMarkers(candleSeries, markers as any);
    }

    // Volume series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });

    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    const volumeData = candles.map((c) => ({
      time: (new Date(c.timestamp).getTime() / 1000) as number,
      value: parseFloat(c.volume),
      color: parseFloat(c.close) >= parseFloat(c.open) ? "#22c55e40" : "#ef444440",
    }));

    volumeSeries.setData(volumeData as any);

    chart.timeScale().fitContent();

    // Resize observer
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
  }, [candles, height, signals]);

  return <div ref={containerRef} className="rounded-xl overflow-hidden border border-[var(--card-border)]" />;
}
