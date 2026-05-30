"use client";

import { useMemo } from "react";

const scale = [
  { max: 50, color: "#2f9f5b", label: "Good" },
  { max: 100, color: "#f0c419", label: "Moderate" },
  { max: 150, color: "#f28c28", label: "Sensitive" },
  { max: 200, color: "#d94a38", label: "Unhealthy" },
  { max: 300, color: "#6a2c91", label: "Very Unhealthy" },
  { max: 500, color: "#5b1a1a", label: "Hazardous" },
];

function getScaleEntry(value: number) {
  return scale.find((entry) => value <= entry.max) ?? scale[scale.length - 1];
}

export default function AQIGauge({ value }: { value: number }) {
  const angle = Math.min(180, Math.max(0, (value / 500) * 180));
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
    </div>
  );
}
