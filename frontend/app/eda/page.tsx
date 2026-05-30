import HourlyHeatmap from "@/components/HourlyHeatmap";
import { fetchEdaSummary } from "@/lib/hopsworks";

export const dynamic = "force-dynamic";

export default async function EdaPage() {
  const summary = await fetchEdaSummary();

  return (
    <>
      <nav className="nav">
        <a href="/">Dashboard</a>
        <a href="/eda">EDA</a>
        <a href="/models">Models</a>
        <a href="/explain">Explain</a>
      </nav>

      <h1 className="section-title">Exploratory Analysis</h1>
      <section className="grid grid-2">
        <div className="card">
          <h2 className="section-title">AQI Distribution</h2>
          <p>{summary.distribution_note}</p>
        </div>
        <div className="card">
          <h2 className="section-title">Seasonality</h2>
          <p>{summary.seasonality_note}</p>
        </div>
      </section>

      <div className="card" style={{ marginTop: 24 }}>
        <h2 className="section-title">Hourly AQI Heatmap</h2>
        <HourlyHeatmap data={summary.hourly_heatmap} />
      </div>
    </>
  );
}
