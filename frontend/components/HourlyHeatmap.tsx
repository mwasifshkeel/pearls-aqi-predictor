"use client";

import { HeatmapCell } from "@/lib/types";

export default function HourlyHeatmap({ data }: { data: HeatmapCell[] }) {
  if (!data.length) {
    return <div>No heatmap data yet.</div>;
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(24, 1fr)", gap: 4 }}>
      {data.map((cell) => (
        <div
          key={`${cell.day}-${cell.hour}`}
          style={{
            height: 18,
            borderRadius: 4,
            background: `rgba(194, 60, 42, ${0.15 + cell.value / 200})`,
          }}
          title={`Day ${cell.day}, Hour ${cell.hour}: ${cell.value}`}
        />
      ))}
    </div>
  );
}
