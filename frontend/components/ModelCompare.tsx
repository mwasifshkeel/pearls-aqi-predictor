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
          <th>RMSE Day 1</th>
          <th>RMSE Day 2</th>
          <th>RMSE Day 3</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.model_name}>
            <td>{row.model_name}</td>
            <td>{Number.isFinite(row.rmse) ? row.rmse.toFixed(2) : "-"}</td>
            <td>{Number.isFinite(row.mae) ? row.mae.toFixed(2) : "-"}</td>
            <td>{Number.isFinite(row.r2) ? row.r2.toFixed(2) : "-"}</td>
            <td>{row.rmse_day1?.toFixed(2) ?? "-"}</td>
            <td>{row.rmse_day2?.toFixed(2) ?? "-"}</td>
            <td>{row.rmse_day3?.toFixed(2) ?? "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
