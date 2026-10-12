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

type RegionValues = Record<string, number>;

type OfficialRegion = {
  name: string;
  labelLocation: { latitude: number; longitude: number };
};

type OfficialAirItem = {
  timestamp: string;
  updatedTimestamp: string;
  readings: {
    psi_twenty_four_hourly?: RegionValues;
    pm25_twenty_four_hourly?: RegionValues;
    pm25_one_hourly?: RegionValues;
  };
};

type OfficialAirResponse = {
  code: number;
  data: { regionMetadata: OfficialRegion[]; items: OfficialAirItem[] };
};

type OfficialWeatherResponse = {
  code: number;
  data: {
    area_metadata: Array<{
      name: string;
      label_location: { latitude: number; longitude: number };
    }>;
    items: Array<{
      update_timestamp: string;
      valid_period: { start: string; end: string };
      forecasts: Array<{ area: string; forecast: string }>;
    }>;
  };
};

const apiUrl = process.env.NEXT_PUBLIC_FLUXSG_API_URL?.replace(/\/$/, "") || null;
const officialUrls = {
  weather: "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast",
  psi: "https://api-open.data.gov.sg/v2/real-time/api/psi",
  pm25: "https://api-open.data.gov.sg/v2/real-time/api/pm25",
};

async function request<T>(path: string): Promise<T | null> {
  if (!apiUrl) return null;
  try {
    const response = await fetch(`${apiUrl}${path}`);
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function officialRequest<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export function psiLevel(value: number): string {
  if (value <= 50) return "Good";
  if (value <= 100) return "Moderate";
  if (value <= 200) return "Unhealthy";
  if (value <= 300) return "Very Unhealthy";
  return "Hazardous";
}

const guidance: Record<string, [string, string]> = {
  Good: ["Normal activities can continue.", "Normal activities can continue."],
  Moderate: [
    "Normal activities can generally continue.",
    "People unusually sensitive to air pollution can reduce prolonged or strenuous outdoor activity.",
  ],
  Unhealthy: [
    "Reduce prolonged or strenuous outdoor activity.",
    "Children, older adults, pregnant people, and people with heart or lung conditions should minimise prolonged or strenuous outdoor activity.",
  ],
  "Very Unhealthy": [
    "Avoid prolonged or strenuous outdoor activity.",
    "Avoid outdoor activity where possible and follow official health advice.",
  ],
  Hazardous: [
    "Minimise outdoor activity and follow official emergency health advice.",
    "Remain indoors where possible and follow official emergency health advice.",
  ],
};

async function getOfficialWeather(): Promise<WeatherOutlook | null> {
  const payload = await officialRequest<OfficialWeatherResponse>(officialUrls.weather);
  const item = payload?.data.items[0];
  if (!payload || payload.code !== 0 || !item) return null;

  const locations = new Map(payload.data.area_metadata.map((area) => [area.name, area.label_location]));
  const issues: string[] = [];
  const forecasts = item.forecasts.flatMap((forecast) => {
    const location = locations.get(forecast.area);
    if (!location || !forecast.forecast.trim()) {
      issues.push(`Invalid forecast for ${forecast.area}`);
      return [];
    }
    return [{
      area: forecast.area,
      forecast: forecast.forecast.trim(),
      latitude: location.latitude,
      longitude: location.longitude,
    }];
  });
  const completeness = item.forecasts.length
    ? Math.round((forecasts.length / item.forecasts.length) * 1000) / 10
    : 0;

  return {
    source: "data.gov.sg / NEA",
    source_url: officialUrls.weather,
    source_updated_at: item.update_timestamp,
    ingested_at: new Date().toISOString(),
    valid_from: item.valid_period.start,
    valid_to: item.valid_period.end,
    forecasts,
    quality: {
      status: completeness === 100 ? "healthy" : "degraded",
      received_records: item.forecasts.length,
      valid_records: forecasts.length,
      completeness_percent: completeness,
      issues,
    },
  };
}

async function getOfficialAirQuality(): Promise<AirQualitySnapshot | null> {
  const [psiPayload, pm25Payload] = await Promise.all([
    officialRequest<OfficialAirResponse>(officialUrls.psi),
    officialRequest<OfficialAirResponse>(officialUrls.pm25),
  ]);
  const psiItem = psiPayload?.data.items[0];
  const pm25Item = pm25Payload?.data.items[0];
  if (!psiPayload || !pm25Payload || psiPayload.code !== 0 || pm25Payload.code !== 0 || !psiItem || !pm25Item) {
    return null;
  }

  const psiValues = psiItem.readings.psi_twenty_four_hourly ?? {};
  const pm25Day = psiItem.readings.pm25_twenty_four_hourly ?? {};
  const pm25Hour = pm25Item.readings.pm25_one_hourly ?? {};
  const issues: string[] = [];
  const regions = psiPayload.data.regionMetadata.flatMap((region) => {
    const psi = psiValues[region.name];
    const day = pm25Day[region.name];
    const hour = pm25Hour[region.name];
    if (psi === undefined || day === undefined || hour === undefined) {
      issues.push(`${region.name}: incomplete official reading`);
      return [];
    }
    return [{
      region: region.name,
      latitude: region.labelLocation.latitude,
      longitude: region.labelLocation.longitude,
      psi_24h: psi,
      pm25_24h: day,
      pm25_1h: hour,
      level: psiLevel(psi),
    }];
  }).sort((a, b) => b.psi_24h - a.psi_24h);
  if (!regions.length) return null;

  const nationalPsi = Math.max(...regions.map((region) => region.psi_24h));
  const level = psiLevel(nationalPsi);
  const [generalPopulation, sensitiveGroups] = guidance[level];
  const completeness = Math.round((regions.length / psiPayload.data.regionMetadata.length) * 1000) / 10;

  return {
    source: "data.gov.sg / NEA",
    source_urls: [officialUrls.psi, officialUrls.pm25],
    observed_at: psiItem.timestamp > pm25Item.timestamp ? psiItem.timestamp : pm25Item.timestamp,
    updated_at: psiItem.updatedTimestamp > pm25Item.updatedTimestamp
      ? psiItem.updatedTimestamp
      : pm25Item.updatedTimestamp,
    ingested_at: new Date().toISOString(),
    national_psi: nationalPsi,
    national_level: level,
    haze_alert: nationalPsi > 100,
    regions,
    guidance: {
      level,
      general_population: generalPopulation,
      sensitive_groups: sensitiveGroups,
      source_url: "https://www.haze.gov.sg/",
      disclaimer: "General information only. Follow current NEA, MOH, school, workplace, and medical advice.",
    },
    quality: {
      status: completeness === 100 ? "healthy" : "degraded",
      received_records: psiPayload.data.regionMetadata.length,
      valid_records: regions.length,
      completeness_percent: completeness,
      issues,
    },
  };
}

export async function getWeather(): Promise<WeatherOutlook | null> {
  return (await request<WeatherOutlook>("/api/v1/weather/outlook")) ?? getOfficialWeather();
}

export async function getLtaStatus(): Promise<LtaStatus> {
  return (await request<LtaStatus>("/api/v1/integrations/lta")) ?? {
    source: "LTA DataMall",
    configured: false,
    state: "planned",
    next_step: "Transport feeds join in Milestone 2",
  };
}

export async function getAirQuality(): Promise<AirQualitySnapshot | null> {
  return (await request<AirQualitySnapshot>("/api/v1/air-quality/current"))
    ?? getOfficialAirQuality();
}

