"use client";

import { ShapSummary } from "@/lib/types";

export default function FeatureImportanceBar({ data }: { data: ShapSummary }) {
  if (!data.features.length) {
    return <div>No SHAP data yet.</div>;
  }

  const max = Math.max(...data.importance, 1);

  return (
    <div style={{ display: "grid", gap: 10 }}>
      {data.features.map((feature, idx) => {
        const value = data.importance[idx] ?? 0;
        return (
          <div key={feature}>
            <div style={{ fontSize: 14, marginBottom: 4 }}>{feature}</div>
            <div
              style={{
                height: 10,
                borderRadius: 6,
                background: "rgba(194, 60, 42, 0.18)",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${(value / max) * 100}%`,
                  borderRadius: 6,
                  background: "#c23c2a",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
