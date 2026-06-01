import { MongoClient } from "mongodb";

import type {
  CurrentAQI,
  EdaSummary,
  ModelMetric,
  PredictionRow,
  RegistryModelSummary,
  ShapSummary,
} from "@/lib/types";

type MongoDoc = Record<string, unknown>;

const uri = process.env.MONGO_URI;
const dbName = process.env.MONGO_DB_NAME ?? "aqi_predictor";
const dagshubUri = process.env.DAGSHUB_MLFLOW_URI ?? process.env.MLFLOW_TRACKING_URI;
const dagshubUser = process.env.DAGSHUB_USERNAME ?? process.env.MLFLOW_TRACKING_USERNAME;
const dagshubToken = process.env.DAGSHUB_TOKEN ?? process.env.MLFLOW_TRACKING_PASSWORD;
const dagshubStage = process.env.DAGSHUB_MODEL_STAGE ?? "Production";

if (!uri) {
  throw new Error("MONGO_URI is required");
}

function encodeBasicAuth(username?: string, token?: string) {
  if (!username || !token) {
    return null;
  }
  return Buffer.from(`${username}:${token}`).toString("base64");
}

async function dagshubRequest<T>(path: string, params?: Record<string, string>) {
  if (!dagshubUri || !dagshubUser || !dagshubToken) {
    return null;
  }
  const url = new URL(`${dagshubUri.replace(/\/$/, "")}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }
  const auth = encodeBasicAuth(dagshubUser, dagshubToken);
  const response = await fetch(url, {
    headers: auth ? { Authorization: `Basic ${auth}` } : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as T;
}

async function dagshubPost<T>(path: string, payload: Record<string, unknown>) {
  if (!dagshubUri || !dagshubUser || !dagshubToken) {
    return null;
  }
  const auth = encodeBasicAuth(dagshubUser, dagshubToken);
  const response = await fetch(`${dagshubUri.replace(/\/$/, "")}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(auth ? { Authorization: `Basic ${auth}` } : {}),
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as T;
}

declare global {
  // eslint-disable-next-line no-var
  var _mongoClientPromise: Promise<MongoClient> | undefined;
}

const client = new MongoClient(uri);
const clientPromise = global._mongoClientPromise ?? client.connect();
if (!global._mongoClientPromise) {
  global._mongoClientPromise = clientPromise;
}

async function getDb() {
  const mongoClient = await clientPromise;
  return mongoClient.db(dbName);
}

function toNumber(value: unknown, fallback = 0) {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  if (value && typeof value === "object" && "toString" in value) {
    const parsed = Number(String(value));
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
}

function toOptionalNumber(value: unknown) {
  if (value === null || value === undefined) {
    return undefined;
  }
  const parsed = toNumber(value, Number.NaN);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function toIsoString(value: unknown) {
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (typeof value === "string") {
    return new Date(value).toISOString();
  }
  return new Date().toISOString();
}

function formatTimeAgo(value: unknown) {
  if (!value) {
    return "unknown";
  }
  const date = value instanceof Date ? value : new Date(String(value));
  const deltaMs = Date.now() - date.getTime();
  if (Number.isNaN(deltaMs)) {
    return "unknown";
  }
  const minutes = Math.floor(deltaMs / 60000);
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export async function fetchCurrent(): Promise<CurrentAQI> {
  const db = await getDb();
  const baseCollection = db.collection("aqi_features_rawalpindi");
  const latest = await baseCollection
    .find({
      european_aqi: { $exists: true },
      pm2_5: { $exists: true },
      pm10: { $exists: true },
      wind_speed_10m: { $exists: true },
      relative_humidity_2m: { $exists: true },
    })
    .sort({ timestamp: -1 })
    .limit(1)
    .next();
  const fallback =
    latest ??
    (await baseCollection
      .find()
      .sort({ timestamp: -1 })
      .limit(1)
      .next());

  const modelMeta = await db
    .collection<{ _id: string; best_model_name?: string }>(
      "aqi_model_metadata_rawalpindi"
    )
    .findOne({ _id: "latest" });

  const modelName = (modelMeta?.best_model_name as string | undefined) ??
    (fallback?.model_name as string | undefined) ??
    "unavailable";

  if (!fallback) {
    return {
      timestamp: new Date().toISOString(),
      european_aqi: 0,
      pm2_5: 0,
      pm10: 0,
      wind_speed_10m: 0,
      relative_humidity_2m: 0,
      model_name: modelName,
      updated_ago: "unknown",
    };
  }

  return {
    timestamp: toIsoString(fallback.timestamp),
    european_aqi: toNumber(fallback.european_aqi),
    pm2_5: toNumber(fallback.pm2_5),
    pm10: toNumber(fallback.pm10),
    wind_speed_10m: toNumber(fallback.wind_speed_10m),
    relative_humidity_2m: toNumber(fallback.relative_humidity_2m),
    model_name: modelName,
    updated_ago: formatTimeAgo(fallback.timestamp),
  };
}

export async function fetchPredictions(): Promise<PredictionRow[]> {
  const db = await getDb();
  const predCollection = db.collection("aqi_predictions_rawalpindi");
  const modelMeta = await db
    .collection<{ _id: string; best_model_name?: string }>(
      "aqi_model_metadata_rawalpindi"
    )
    .findOne({ _id: "latest" });

  let modelName = modelMeta?.best_model_name as string | undefined;
  if (!modelName) {
    const latest = await predCollection
      .find()
      .sort({ timestamp: -1 })
      .limit(1)
      .next();
    modelName = latest?.model_name as string | undefined;
  }
  if (!modelName) {
    return [];
  }

  const rows = await predCollection
    .find({ model_name: modelName })
    .sort({ horizon_hours: 1 })
    .limit(72)
    .toArray();

  return rows.map((row) => ({
    timestamp: toIsoString(row.timestamp),
    predicted_aqi: toNumber(row.predicted_aqi),
    model_name: modelName as string,
    horizon_hours: toNumber(row.horizon_hours),
    confidence_lower: toNumber(row.confidence_lower),
    confidence_upper: toNumber(row.confidence_upper),
  }));
}

export async function fetchShapSummary(): Promise<ShapSummary> {
  const db = await getDb();
  const doc = await db
    .collection<{ _id: string; features?: string[]; importance?: number[] }>(
      "aqi_shap_summary_rawalpindi"
    )
    .findOne({ _id: "latest" });

  if (!doc) {
    return { features: [], importance: [] };
  }

  return {
    features: (doc.features as string[]) ?? [],
    importance: (doc.importance as number[]) ?? [],
  };
}

export async function fetchModelMetrics(): Promise<ModelMetric[]> {
  const db = await getDb();
  const rows = await db
    .collection("aqi_model_metrics_rawalpindi")
    .find()
    .sort({ rmse: 1 })
    .toArray();

  return rows.map((row) => ({
    model_name: String(row.model_name ?? "unknown"),
    rmse: toNumber(row.rmse),
    mae: toNumber(row.mae),
    r2: toNumber(row.r2),
    rmse_24h: row.rmse_24h !== undefined ? toNumber(row.rmse_24h) : undefined,
    rmse_48h: row.rmse_48h !== undefined ? toNumber(row.rmse_48h) : undefined,
    rmse_72h: row.rmse_72h !== undefined ? toNumber(row.rmse_72h) : undefined,
  }));
}

export async function fetchRegistrySummary(): Promise<RegistryModelSummary | null> {
  const db = await getDb();
  const modelMeta = await db
    .collection<{ _id: string; best_model_name?: string; updated_at?: string }>(
      "aqi_model_metadata_rawalpindi"
    )
    .findOne({ _id: "latest" });

  const bestName = modelMeta?.best_model_name;
  if (!bestName) {
    return null;
  }

  async function buildFallbackSummary() {
    const metrics = await db
      .collection("aqi_model_metrics_rawalpindi")
      .findOne({ model_name: bestName });
    const fallbackMetrics = metrics ??
      (await db
        .collection("aqi_model_metrics_rawalpindi")
        .find()
        .sort({ rmse: 1 })
        .limit(1)
        .next());

    return {
      name: bestName,
      version: "unknown",
      stage: dagshubStage,
      run_id: String(modelMeta?.best_model_run_id ?? "unknown"),
      source: "",
      metrics: {
        rmse: toOptionalNumber(fallbackMetrics?.rmse),
        mae: toOptionalNumber(fallbackMetrics?.mae),
        r2: toOptionalNumber(fallbackMetrics?.r2),
        rmse_24h: toOptionalNumber(fallbackMetrics?.rmse_24h),
        rmse_48h: toOptionalNumber(fallbackMetrics?.rmse_48h),
        rmse_72h: toOptionalNumber(fallbackMetrics?.rmse_72h),
      },
      updated_at: modelMeta?.updated_at,
    };
  }

  const modelName = `${bestName}_aqi_rawalpindi`;
  const latest = await dagshubPost<{
    model_versions?: Array<{
      name?: string;
      version?: string;
      current_stage?: string;
      run_id?: string;
      source?: string;
    }>;
  }>("/api/2.0/mlflow/registered-models/get-latest-versions", {
    name: modelName,
    stages: [dagshubStage],
  });

  const version = latest?.model_versions?.[0];
  if (!version?.run_id) {
    return buildFallbackSummary();
  }

  const run = await dagshubRequest<{
    run?: { data?: { metrics?: Array<{ key: string; value: number }> } };
  }>("/api/2.0/mlflow/runs/get", { run_id: version.run_id });

  if (!run) {
    return buildFallbackSummary();
  }

  const metrics = new Map(
    (run?.run?.data?.metrics ?? []).map((metric) => [metric.key, metric.value])
  );

  return {
    name: version.name ?? modelName,
    version: version.version ?? "unknown",
    stage: version.current_stage ?? dagshubStage,
    run_id: version.run_id,
    source: version.source ?? "",
    metrics: {
      rmse: metrics.get("rmse"),
      mae: metrics.get("mae"),
      r2: metrics.get("r2"),
      rmse_24h: metrics.get("rmse_24h"),
      rmse_48h: metrics.get("rmse_48h"),
      rmse_72h: metrics.get("rmse_72h"),
    },
    updated_at: modelMeta?.updated_at,
  };
}

export async function fetchEdaSummary(): Promise<EdaSummary> {
  const db = await getDb();
  const doc = await db
    .collection<{
      _id: string;
      distribution_note?: string;
      seasonality_note?: string;
      hourly_heatmap?: MongoDoc[];
    }>("aqi_eda_summary_rawalpindi")
    .findOne({ _id: "latest" });

  if (!doc) {
    return {
      distribution_note: "No EDA summary available yet.",
      seasonality_note: "No seasonality summary available yet.",
      hourly_heatmap: [],
    };
  }

  return {
    distribution_note: String(doc.distribution_note ?? ""),
    seasonality_note: String(doc.seasonality_note ?? ""),
    hourly_heatmap: (doc.hourly_heatmap as MongoDoc[])?.map((cell) => ({
      day: toNumber(cell.day),
      hour: toNumber(cell.hour),
      value: toNumber(cell.value),
    })) ?? [],
  };
}
