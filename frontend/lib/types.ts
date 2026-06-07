export type PredictionRow = {
  timestamp: string;
  predicted_aqi: number;
  model_name: string;
  horizon_days: number;
  confidence_lower: number;
  confidence_upper: number;
};

export type CurrentAQI = {
  timestamp: string;
  european_aqi: number;
  pm2_5: number;
  pm10: number;
  wind_speed_10m: number;
  relative_humidity_2m: number;
  model_name: string;
  updated_ago: string;
};

export type ShapSummary = {
  features: string[];
  importance: number[];
};

export type ModelMetric = {
  model_name: string;
  rmse: number;
  mae: number;
  r2: number;
  rmse_day1?: number;
  rmse_day2?: number;
  rmse_day3?: number;
  r2_day1?: number;
  r2_day2?: number;
  r2_day3?: number;
};
export type RegistryModelSummary = {
  name: string;
  model_name?: string;
  registry_name?: string;
  stage: string;
  run_id?: string;
  version?: string;
  source?: string;
  dagshub_url?: string;
  metrics: {
    rmse?: number;
    mae?: number;
    r2?: number;
    rmse_day1?: number;
    rmse_day2?: number;
    rmse_day3?: number;
    r2_day1?: number;
    r2_day2?: number;
    r2_day3?: number;
  };
  updated_at?: string;
};

export type HeatmapCell = {
  day: number;
  hour: number;
  value: number;
};

export type EdaSummary = {
  distribution_note: string;
  seasonality_note: string;
  hourly_heatmap: HeatmapCell[];
};
