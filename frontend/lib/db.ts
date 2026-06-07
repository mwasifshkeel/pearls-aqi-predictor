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
  const modelStage = process.env.MODEL_STAGE ?? "Production";

  if (!uri) {
    throw new Error("MONGO_URI is required");
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

  type DagsHubConfig = {
    baseUrl: string;
    username: string;
    token: string;
    stage: string;
    repoUrl?: string;
  };

  function getDagsHubConfig(): DagsHubConfig | null {
    const baseUrl =
      process.env.DAGSHUB_MLFLOW_URI ?? process.env.MLFLOW_TRACKING_URI;
    const username =
      process.env.DAGSHUB_USERNAME ?? process.env.MLFLOW_TRACKING_USERNAME;
    const token =
      process.env.DAGSHUB_TOKEN ?? process.env.MLFLOW_TRACKING_PASSWORD;
    if (!baseUrl || !username || !token) {
      return null;
    }
    const trimmed = baseUrl.replace(/\/+$/, "");
    const repoUrl = trimmed.endsWith(".mlflow")
      ? trimmed.replace(/\.mlflow$/, "")
      : undefined;
    return {
      baseUrl: trimmed,
      username,
      token,
      stage: modelStage,
      repoUrl,
    };
  }

  function toIsoFromMs(value: unknown) {
    if (typeof value === "number") {
      return new Date(value).toISOString();
    }
    return undefined;
  }

  async function fetchDagsHubLatestModel(
    modelName: string | undefined
  ): Promise<Record<string, unknown> | null> {
    if (!modelName) {
      return null;
    }
    const config = getDagsHubConfig();
    if (!config) {
      return null;
    }
    const auth = Buffer.from(`${config.username}:${config.token}`).toString(
      "base64"
    );
    const response = await fetch(
      `${config.baseUrl}/api/2.0/mlflow/registered-models/get-latest-versions`,
      {
        method: "POST",
        headers: {
          Authorization: `Basic ${auth}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: modelName, stages: [config.stage] }),
        cache: "no-store",
      }
    );
    if (!response.ok) {
      return null;
    }
    const payload = (await response.json()) as {
      model_versions?: Record<string, unknown>[];
    };
    return payload.model_versions?.[0] ?? null;
  }

  export async function fetchCurrent(): Promise<CurrentAQI> {
    const db = await getDb();
    const baseCollection = db.collection("aqi_features_rawalpindi");
    const now = new Date();
    const latest = await baseCollection
      .find({
        european_aqi: { $exists: true },
        pm2_5: { $exists: true },
        pm10: { $exists: true },
        wind_speed_10m: { $exists: true },
        relative_humidity_2m: { $exists: true },
        timestamp: { $lte: now },
      })
      .sort({ timestamp: -1 })
      .limit(1)
      .next();
    const fallback =
      latest ??
      (await baseCollection
        .find({ timestamp: { $lte: now } })
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
      .sort({ horizon_days: 1 })
      .limit(3)
      .toArray();

    return rows.map((row) => ({
      timestamp: toIsoString(row.timestamp),
      predicted_aqi: toNumber(row.predicted_aqi),
      model_name: modelName as string,
      horizon_days: toNumber(row.horizon_days),
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
          rmse_day1: row.rmse_day1 !== undefined ? toNumber(row.rmse_day1) : undefined,
          rmse_day2: row.rmse_day2 !== undefined ? toNumber(row.rmse_day2) : undefined,
          rmse_day3: row.rmse_day3 !== undefined ? toNumber(row.rmse_day3) : undefined,
          r2_day1: row.r2_day1 !== undefined ? toNumber(row.r2_day1) : undefined,
          r2_day2: row.r2_day2 !== undefined ? toNumber(row.r2_day2) : undefined,
          r2_day3: row.r2_day3 !== undefined ? toNumber(row.r2_day3) : undefined,
      }));
  }

  export async function fetchRegistrySummary(): Promise<RegistryModelSummary | null> {
    const db = await getDb();

    const modelMeta = await db
      .collection<{
        _id: string;
        best_model_name?: string;
        best_model_registry_name?: string;
        best_model_run_id?: string;
        best_model_version?: string;
        updated_at?: string;
      }>("aqi_model_metadata_rawalpindi")
      .findOne({ _id: "latest" });

    const bestName = modelMeta?.best_model_name;
    const registryName =
      modelMeta?.best_model_registry_name ??
      (bestName ? `${bestName}_aqi_rawalpindi` : undefined);

    if (!bestName || !registryName) {
      return null;
    }

    const dagshubVersion = await fetchDagsHubLatestModel(registryName);

    const metrics =
      (await db
        .collection("aqi_model_metrics_rawalpindi")
        .findOne({ model_name: bestName })) ??
      (await db
        .collection("aqi_model_metrics_rawalpindi")
        .find()
        .sort({ rmse: 1 })
        .limit(1)
        .next());

    return {
      name: bestName,
      model_name: bestName,
      registry_name: registryName,

      stage:
        (dagshubVersion?.current_stage as string | undefined) ??
        modelStage,

      run_id:
        (dagshubVersion?.run_id as string | undefined) ??
        modelMeta?.best_model_run_id,

      version:
        (dagshubVersion?.version as string | undefined) ??
        modelMeta?.best_model_version,

      source: dagshubVersion?.source as string | undefined,

      dagshub_url: (() => {
        const config = getDagsHubConfig();
        if (!config?.repoUrl) return undefined;
        return `${config.repoUrl}/models/${registryName}`;
      })(),

      metrics: {
        rmse: toOptionalNumber(metrics?.rmse),
        mae: toOptionalNumber(metrics?.mae),
        r2: toOptionalNumber(metrics?.r2),
        rmse_day1: toOptionalNumber(metrics?.rmse_day1),
        rmse_day2: toOptionalNumber(metrics?.rmse_day2),
        rmse_day3: toOptionalNumber(metrics?.rmse_day3),
        r2_day1: toOptionalNumber(metrics?.r2_day1),
        r2_day2: toOptionalNumber(metrics?.r2_day2),
        r2_day3: toOptionalNumber(metrics?.r2_day3),
      },

      updated_at:
        toIsoFromMs(dagshubVersion?.last_updated_timestamp) ??
        modelMeta?.updated_at,
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
