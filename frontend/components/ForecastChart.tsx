"use client";

import { PredictionRow } from "@/lib/types";

export default function ForecastChart({ data }: { data: PredictionRow[] }) {
  if (!data.length) {
    return <div>No forecast data yet.</div>;
  }

  const max = Math.max(
    ...data.map((row) => row.confidence_upper ?? row.predicted_aqi),
    200
  );
  const min = Math.min(
    ...data.map((row) => row.confidence_lower ?? row.predicted_aqi),
    0
  );
  const scaleY = (value: number) => 160 - ((value - min) / (max - min + 1)) * 140;

  const points = data.map((row, idx) => {
    const x = 10 + (idx / (data.length - 1)) * 360;
    const y = scaleY(row.predicted_aqi);
    return `${x},${y}`;
  });

  const upperBand = data.map((row, idx) => {
    const x = 10 + (idx / (data.length - 1)) * 360;
    const y = scaleY(row.confidence_upper ?? row.predicted_aqi);
    return `${x},${y}`;
  });

  const lowerBand = data
    .map((row, idx) => {
      const x = 10 + (idx / (data.length - 1)) * 360;
      const y = scaleY(row.confidence_lower ?? row.predicted_aqi);
      return `${x},${y}`;
    })
    .reverse();

  return (
    <svg width="100%" height="180" viewBox="0 0 380 180">
      <defs>
        <linearGradient id="aqiBand" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#0f6b5d" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#0f6b5d" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      <polygon
        points={[...upperBand, ...lowerBand].join(" ")}
        fill="url(#aqiBand)"
        stroke="none"
      />
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke="#0f6b5d"
        strokeWidth="3"
      />
      {points.map((point, idx) => {
        const [x, y] = point.split(",").map(Number);
        return <circle key={idx} cx={x} cy={y} r={2.5} fill="#c23c2a" />;
      })}
    </svg>
  );
}
