"use client";

import { useMemo } from "react";

const scale = [
  { max: 20, color: "#50F0E6", label: "Good" },
  { max: 40, color: "#50CCAA", label: "Fair" },
  { max: 60, color: "#F0E641", label: "Moderate" },
  { max: 80, color: "#FF5050", label: "Poor" },
  { max: 100, color: "#960032", label: "Very Poor" },
  { max: Infinity, color: "#7D2181", label: "Extremely Poor" },
];

function getScaleEntry(value: number) {
  return scale.find((entry) => value <= entry.max) ?? scale[scale.length - 1];
}

export default function AQIGauge({ value }: { value: number }) {
  const MAX_GAUGE_VALUE = 120;

  const angle = Math.min(
    180,
    Math.max(0, (Math.min(value, MAX_GAUGE_VALUE) / MAX_GAUGE_VALUE) * 180)
  );
  const entry = useMemo(() => getScaleEntry(value), [value]);

  return (
    <div style={{ textAlign: "center" }}>
      <svg width="240" height="140" viewBox="0 0 240 140">
        <path
          d="M20,120 A100,100 0 0,1 220,120"
          stroke="#e5e1d8"
          strokeWidth="20"
          fill="none"
        />
        <path
          d="M20,120 A100,100 0 0,1 220,120"
          stroke={entry.color}
          strokeWidth="20"
          fill="none"
          strokeDasharray={`${(angle / 180) * 314} 314`}
        />
        <line
          x1="120"
          y1="120"
          x2={120 + 90 * Math.cos(Math.PI - (angle * Math.PI) / 180)}
          y2={120 - 90 * Math.sin(Math.PI - (angle * Math.PI) / 180)}
          stroke="#1f2a2b"
          strokeWidth="4"
        />
        <circle cx="120" cy="120" r="6" fill="#1f2a2b" />
      </svg>
      <div style={{ fontSize: 40, fontWeight: 700 }}>{value}</div>
      <div style={{ color: entry.color, fontWeight: 600 }}>{entry.label}</div>
      <div style={{ fontSize: 12, color: "#6b6b6b", marginTop: 6 }}>
        European AQI scale (0–100+) · differs from US AQI (0–500)
      </div>
    </div>
  );
}
