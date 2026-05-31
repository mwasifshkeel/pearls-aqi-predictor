import ModelCompare from "@/components/ModelCompare";
import { fetchModelMetrics } from "@/lib/hopsworks";

export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  const models = await fetchModelMetrics();

  return (
    <>
      <nav className="nav">
        <a href="/">Dashboard</a>
        <a href="/eda">EDA</a>
        <a href="/models">Models</a>
        <a href="/explain">Explain</a>
      </nav>

      <h1 className="section-title">Model Benchmarks</h1>
      <div className="card">
        <ModelCompare rows={models} />
      </div>
    </>
  );
}
