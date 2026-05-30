import AQIGauge from "@/components/AQIGauge";
import AlertBanner from "@/components/AlertBanner";
import ForecastChart from "@/components/ForecastChart";
import FeatureImportanceBar from "@/components/FeatureImportanceBar";
import { fetchCurrent, fetchPredictions, fetchShapSummary } from "@/lib/hopsworks";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const current = await fetchCurrent();
  const predictions = await fetchPredictions();
  const shapSummary = await fetchShapSummary();

  const hasAlert = predictions.some((row) => row.predicted_aqi >= 150);

  return (
    <>
      <nav className="nav">
        <a href="/">Dashboard</a>
        <a href="/eda">EDA</a>
        <a href="/models">Models</a>
        <a href="/explain">Explain</a>
      </nav>

      <section className="hero">
        <div>
          <span className="badge">Powered by {current.model_name}</span>
          <h1 className="section-title">Rawalpindi AQI Forecast</h1>
          <p>
            Live air-quality intelligence driven by Open-Meteo and a daily refreshed
            model registry. Updated {current.updated_ago}.
          </p>
        </div>
        <div className="card">
          <AQIGauge value={current.european_aqi} />
        </div>
      </section>

      {hasAlert && <AlertBanner message="Forecast exceeds AQI 150 in the next 72 hours." />}

      <section className="grid grid-2">
        <div className="card">
          <h2 className="section-title">72h Forecast</h2>
          <ForecastChart data={predictions} />
        </div>
        <div className="card">
          <h2 className="section-title">Drivers Right Now</h2>
          <FeatureImportanceBar data={shapSummary} />
        </div>
      </section>

      <section className="section-title">Current Conditions</section>
      <section className="grid grid-3">
        <div className="card">
          <strong>PM2.5</strong>
          <div>{current.pm2_5} µg/m3</div>
        </div>
        <div className="card">
          <strong>PM10</strong>
          <div>{current.pm10} µg/m3</div>
        </div>
        <div className="card">
          <strong>Wind</strong>
          <div>{current.wind_speed_10m} km/h</div>
        </div>
        <div className="card">
          <strong>Humidity</strong>
          <div>{current.relative_humidity_2m}%</div>
        </div>
      </section>
    </>
  );
}
