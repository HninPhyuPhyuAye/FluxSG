export type AreaForecast = {
  area: string;
  forecast: string;
  latitude: number;
  longitude: number;
};

export type WeatherOutlook = {
  source: string;
  source_url: string;
  source_updated_at: string;
  ingested_at: string;
  valid_from: string;
  valid_to: string;
  forecasts: AreaForecast[];
  quality: {
    status: string;
    received_records: number;
    valid_records: number;
    completeness_percent: number;
    issues: string[];
  };
};

export type LtaStatus = {
  source: string;
  configured: boolean;
  state: string;
  next_step: string;
};

export type AirQualitySnapshot = {
  source: string;
  source_urls: string[];
  observed_at: string;
  updated_at: string;
  ingested_at: string;
  national_psi: number;
  national_level: string;
  haze_alert: boolean;
  regions: Array<{
    region: string;
    latitude: number;
    longitude: number;
    psi_24h: number;
    pm25_24h: number;
    pm25_1h: number;
    level: string;
  }>;
  guidance: {
    level: string;
    general_population: string;
    sensitive_groups: string;
    source_url: string;
    disclaimer: string;
  };
  quality: {
    status: string;
    received_records: number;
    valid_records: number;
    completeness_percent: number;
    issues: string[];
  };
};

const apiUrl = process.env.FLUXSG_API_URL ?? "http://localhost:8000";

async function request<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiUrl}${path}`, { next: { revalidate: 300 } });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export function getWeather(): Promise<WeatherOutlook | null> {
  return request<WeatherOutlook>("/api/v1/weather/outlook");
}

export function getLtaStatus(): Promise<LtaStatus | null> {
  return request<LtaStatus>("/api/v1/integrations/lta");
}

export function getAirQuality(): Promise<AirQualitySnapshot | null> {
  return request<AirQualitySnapshot>("/api/v1/air-quality/current");
}

