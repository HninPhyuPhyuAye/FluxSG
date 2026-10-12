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

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

