"use client";

import { ModelMetric } from "@/lib/types";

export default function ModelCompare({ rows }: { rows: ModelMetric[] }) {
  if (!rows.length) {
    return <div>No model metrics yet.</div>;
  }

  return (
    <table className="table">
      <thead>
        <tr>
          <th>Model</th>
          <th>RMSE</th>
          <th>MAE</th>
          <th>R2</th>
          <th>RMSE 24h</th>
          <th>RMSE 48h</th>
          <th>RMSE 72h</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.model_name}>
            <td>{row.model_name}</td>
            <td>{row.rmse.toFixed(2)}</td>
            <td>{row.mae.toFixed(2)}</td>
            <td>{row.r2.toFixed(2)}</td>
            <td>{row.rmse_24h?.toFixed(2) ?? "-"}</td>
            <td>{row.rmse_48h?.toFixed(2) ?? "-"}</td>
            <td>{row.rmse_72h?.toFixed(2) ?? "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
