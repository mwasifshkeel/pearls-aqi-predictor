import AQIGauge from "@/components/AQIGauge";
import AlertBanner from "@/components/AlertBanner";
import ForecastChart from "@/components/ForecastChart";
import FeatureImportanceBar from "@/components/FeatureImportanceBar";
import { fetchCurrent, fetchPredictions, fetchShapSummary } from "@/lib/db";
import type { PredictionRow } from "@/lib/types";

export const dynamic = "force-dynamic";

type DailyForecast = {
  key: string;
  label: string;
  average: number;
  lower: number;
  upper: number;
};

type ForecastHighlights = {
  average: number;
  min: number;
  max: number;
  peakDay: string;
};

const dayFormatter = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: "Asia/Karachi",
});

function sortedDailyPredictions(predictions: PredictionRow[]): PredictionRow[] {
  return predictions
    .slice()
    .sort((a, b) => a.horizon_days - b.horizon_days)
    .slice(0, 3);
}

function buildDailyForecast(predictions: PredictionRow[]): DailyForecast[] {
  return sortedDailyPredictions(predictions).map((row) => {
    const date = new Date(row.timestamp);
    return {
      key: row.timestamp,
      label: Number.isNaN(date.getTime())
        ? `Day ${row.horizon_days}`
        : dayFormatter.format(date),
      average: row.predicted_aqi,
      lower: row.confidence_lower ?? row.predicted_aqi,
      upper: row.confidence_upper ?? row.predicted_aqi,
    };
  });
}

function buildForecastHighlights(
  predictions: PredictionRow[]
): ForecastHighlights | null {
  const days = sortedDailyPredictions(predictions);
  if (!days.length) {
    return null;
  }

  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  let total = 0;
  let peakDate = days[0]?.timestamp ?? "";

  for (const row of days) {
    total += row.predicted_aqi;
    if (row.predicted_aqi < min) {
      min = row.predicted_aqi;
    }
    if (row.predicted_aqi > max) {
      max = row.predicted_aqi;
      peakDate = row.timestamp;
    }
  }

  const peakLabel = peakDate
    ? dayFormatter.format(new Date(peakDate))
    : "unknown";

  return {
    average: total / days.length,
    min,
    max,
    peakDay: peakLabel,
  };
}

export default async function HomePage() {
  const current = await fetchCurrent();
  const predictions = await fetchPredictions();
  const shapSummary = await fetchShapSummary();
  const dailyForecast = buildDailyForecast(predictions);
  const highlights = buildForecastHighlights(predictions);

  const hasAlert = predictions.some((row) => row.predicted_aqi >= 150);
  const hasCurrent = current.updated_ago !== "unknown";

  return (
    <>
      <nav className="nav">
        <a href="/">Dashboard</a>
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

      {hasAlert && <AlertBanner message="Daily average AQI exceeds 150 in the next 3 days." />}

      <section className="section-title">Next 3 Days</section>
      <section className="grid grid-3 forecast-grid">
        {dailyForecast.length ? (
          dailyForecast.map((day) => (
            <div key={day.key} className="card forecast-card">
              <div className="forecast-label">{day.label}</div>
              <div className="forecast-subtitle">Avg AQI</div>
              <div className="forecast-value">{Math.round(day.average)}</div>
              <div className="forecast-range">
                Range {Math.round(day.lower)}–{Math.round(day.upper)}
              </div>
            </div>
          ))
        ) : (
          <div className="card">No forecast data yet.</div>
        )}
      </section>
      <section className="grid grid-2">
        <div className="card">
          <h2 className="section-title">3-Day Forecast</h2>
          {highlights && (
            <div className="forecast-kpis">
              <div className="forecast-kpi">
                <span>Peak Day Avg</span>
                <strong>{Math.round(highlights.max)}</strong>
                <em>{highlights.peakDay}</em>
              </div>
              <div className="forecast-kpi">
                <span>3-Day Avg</span>
                <strong>{Math.round(highlights.average)}</strong>
                <em>AQI units</em>
              </div>
              <div className="forecast-kpi">
                <span>Daily Range</span>
                <strong>
                  {Math.round(highlights.min)}–{Math.round(highlights.max)}
                </strong>
                <em>Low to high</em>
              </div>
            </div>
          )}
          <ForecastChart data={sortedDailyPredictions(predictions)} />
        </div>
        <div className="card">
          <h2 className="section-title">Drivers Right Now</h2>
          <FeatureImportanceBar
            data={{
              features: shapSummary.features.slice(0, 10),
              importance: shapSummary.importance.slice(0, 10),
            }}
          />
        </div>
      </section>

      <section className="section-title">Current Conditions</section>
      <section className="grid grid-3">
        <div className="card">
          <strong>PM2.5</strong>
          <div>{hasCurrent ? `${current.pm2_5} µg/m3` : "--"}</div>
        </div>
        <div className="card">
          <strong>PM10</strong>
          <div>{hasCurrent ? `${current.pm10} µg/m3` : "--"}</div>
        </div>
        <div className="card">
          <strong>Wind</strong>
          <div>{hasCurrent ? `${current.wind_speed_10m} km/h` : "--"}</div>
        </div>
        <div className="card">
          <strong>Humidity</strong>
          <div>{hasCurrent ? `${current.relative_humidity_2m}%` : "--"}</div>
        </div>
        {!hasCurrent && (
          <div className="card">
            <strong>Status</strong>
            <div className="muted">Awaiting latest sensor data.</div>
          </div>
        )}
      </section>
    </>
  );
}
