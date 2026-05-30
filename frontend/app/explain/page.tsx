import FeatureImportanceBar from "@/components/FeatureImportanceBar";
import { fetchShapSummary } from "@/lib/hopsworks";

export const dynamic = "force-dynamic";

export default async function ExplainPage() {
  const shapSummary = await fetchShapSummary();

  return (
    <>
      <nav className="nav">
        <a href="/">Dashboard</a>
        <a href="/eda">EDA</a>
        <a href="/models">Models</a>
        <a href="/explain">Explain</a>
      </nav>

      <h1 className="section-title">Explainability</h1>
      <div className="card">
        <FeatureImportanceBar data={shapSummary} />
      </div>
    </>
  );
}
