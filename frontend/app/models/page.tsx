import ModelCompare from "@/components/ModelCompare";
import { fetchModelMetrics, fetchRegistrySummary } from "@/lib/hopsworks";

export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  const summary = await fetchRegistrySummary();
  const models = await fetchModelMetrics();

  return (
    <>
      <nav className="nav">
        <a href="/">Dashboard</a>
        <a href="/models">Models</a>
        <a href="/explain">Explain</a>
      </nav>

      <h1 className="section-title">Model Registry</h1>
      <div className="grid grid-2">
        <div className="card">
          <h2 className="section-title">Latest Production Model</h2>
          {summary ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div>
                <strong>Registry Name</strong>
                <div>{summary.registry_name ?? summary.name}</div>
              </div>
              {summary.model_name && (
                <div>
                  <strong>Model Key</strong>
                  <div>{summary.model_name}</div>
                </div>
              )}
              <div>
                <strong>Stage</strong>
                <div>{summary.stage}</div>
              </div>
              {summary.version && (
                <div>
                  <strong>Version</strong>
                  <div>{summary.version}</div>
                </div>
              )}
              {summary.run_id && (
                <div>
                  <strong>Run ID</strong>
                  <div>{summary.run_id}</div>
                </div>
              )}
              {summary.dagshub_url && (
                <div>
                  <strong>DagsHub</strong>
                  <div>
                    <a href={summary.dagshub_url} target="_blank" rel="noreferrer">
                      Open model registry
                    </a>
                  </div>
                </div>
              )}
              {summary.updated_at && (
                <div>
                  <strong>Updated</strong>
                  <div>{summary.updated_at}</div>
                </div>
              )}
            </div>
          ) : (
            <div>No registry data yet.</div>
          )}
        </div>
        <div className="card">
         tsx          <h2 className="section-title">Latest Metrics</h2>
          {summary ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div>
                <strong>RMSE</strong>
                <div>{summary.metrics.rmse?.toFixed(2) ?? "-"}</div>
              </div>
              <div>
                <strong>MAE</strong>
                <div>{summary.metrics.mae?.toFixed(2) ?? "-"}</div>
              </div>
              <div>
                <strong>RMSE 24h</strong>
                <div>{summary.metrics.rmse_24h?.toFixed(2) ?? "-"}</div>
              </div>
              <div>
                <strong>R² 24h</strong>
                <div>{summary.metrics.r2_24h?.toFixed(3) ?? "-"}</div>
              </div>
              <div>
                <strong>RMSE 48h</strong>
                <div>{summary.metrics.rmse_48h?.toFixed(2) ?? "-"}</div>
              </div>
              <div>
                <strong>R² 48h</strong>
                <div>{summary.metrics.r2_48h?.toFixed(3) ?? "-"}</div>
              </div>
              <div>
                <strong>RMSE 72h</strong>
                <div>{summary.metrics.rmse_72h?.toFixed(2) ?? "-"}</div>
              </div>
              <div>
                <strong>R² 72h</strong>
                <div>{summary.metrics.r2_72h?.toFixed(3) ?? "-"}</div>
              </div>
            </div>
          ) : (
            <div>No metrics yet.</div>
          )}
        </div>
      </div>

      <h2 className="section-title">Daily Training Benchmarks</h2>
      <div className="card">
        <ModelCompare rows={models} />
      </div>
    </>
  );
}
