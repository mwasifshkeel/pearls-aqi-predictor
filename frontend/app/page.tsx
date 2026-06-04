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
  min: number;
  max: number;
  peakHour: string;
};

type ForecastHighlights = {
  average: number;
  min: number;
  max: number;
  peakTime: string;
};

const dayFormatter = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: "Asia/Karachi",
});

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  timeZone: "Asia/Karachi",
});

function buildDailyForecast(predictions: PredictionRow[]): DailyForecast[] {
  const byDay = new Map<
    string,
    { date: Date; values: number[]; peakValue: number; peakTime: Date }
  >();

  for (const row of predictions) {
    const stamp = new Date(row.timestamp);
    if (Number.isNaN(stamp.getTime())) {
      continue;
    }
    const key = stamp.toISOString().slice(0, 10);
    const entry = byDay.get(key);
    if (!entry) {
      byDay.set(key, {
        date: stamp,
        values: [row.predicted_aqi],
        peakValue: row.predicted_aqi,
        peakTime: stamp,
      });
    } else {
      entry.values.push(row.predicted_aqi);
      if (row.predicted_aqi > entry.peakValue) {
        entry.peakValue = row.predicted_aqi;
        entry.peakTime = stamp;
      }
    }
  }

  return Array.from(byDay.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(0, 3)
    .map(([key, entry]) => {
      const total = entry.values.reduce((sum, value) => sum + value, 0);
      const min = Math.min(...entry.values);
      const max = Math.max(...entry.values);
      return {
        key,
        label: dayFormatter.format(entry.date),
        average: total / entry.values.length,
        min,
        max,
        peakHour: timeFormatter.format(entry.peakTime),
      };
    });
}

function buildForecastHighlights(
  predictions: PredictionRow[]
): ForecastHighlights | null {
  if (!predictions.length) {
    return null;
  }

  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  let total = 0;
  let peakTime = predictions[0]?.timestamp ?? "";

  for (const row of predictions) {
    total += row.predicted_aqi;
    if (row.predicted_aqi < min) {
      min = row.predicted_aqi;
    }
    if (row.predicted_aqi > max) {
      max = row.predicted_aqi;
      peakTime = row.timestamp;
    }
  }

  const peakLabel = peakTime
    ? timeFormatter.format(new Date(peakTime))
    : "unknown";

  return {
    average: total / predictions.length,
    min,
    max,
    peakTime: peakLabel,
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

      {hasAlert && <AlertBanner message="Forecast exceeds AQI 150 in the next 72 hours." />}

      <section className="section-title">Next 3 Days</section>
      <section className="grid grid-3 forecast-grid">
        {dailyForecast.length ? (
          dailyForecast.map((day) => (
            <div key={day.key} className="card forecast-card">
              <div className="forecast-label">{day.label}</div>
              <div className="forecast-subtitle">Avg AQI</div>
              <div className="forecast-value">{Math.round(day.average)}</div>
              <div className="forecast-range">
                Range {Math.round(day.min)}–{Math.round(day.max)}
              </div>
              <div className="forecast-meta">
                Peak {Math.round(day.max)} around {day.peakHour}
              </div>
            </div>
          ))
        ) : (
          <div className="card">No forecast data yet.</div>
        )}
      </section>
      <section className="grid grid-2">
        <div className="card">
          <h2 className="section-title">72h Forecast</h2>
          {highlights && (
            <div className="forecast-kpis">
              <div className="forecast-kpi">
                <span>72h Peak</span>
                <strong>{Math.round(highlights.max)}</strong>
                <em>{highlights.peakTime}</em>
              </div>
              <div className="forecast-kpi">
                <span>72h Avg</span>
                <strong>{Math.round(highlights.average)}</strong>
                <em>AQI units</em>
              </div>
              <div className="forecast-kpi">
                <span>72h Range</span>
                <strong>
                  {Math.round(highlights.min)}–{Math.round(highlights.max)}
                </strong>
                <em>Low to high</em>
              </div>
            </div>
          )}
          <ForecastChart data={predictions} />
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
