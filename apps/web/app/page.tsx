"use client";

import {
  getAirQuality,
  getBusArrivals,
  getForecast,
  getLtaStatus,
  getTransportNetwork,
  getWeather,
  searchBusStops,
} from "@/lib/api";
import { useEffect, useState } from "react";
import type {
  AirQualitySnapshot,
  BusArrivalBoard,
  BusStop,
  ForecastSnapshot,
  LtaStatus,
  TransportNetworkSummary,
  WeatherOutlook,
} from "@/lib/api";

function formatTime(value?: string): string {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat("en-SG", {
    timeZone: "Asia/Singapore",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function Home() {
  const [weather, setWeather] = useState<WeatherOutlook | null>(null);
  const [airQuality, setAirQuality] = useState<AirQualitySnapshot | null>(null);
  const [lta, setLta] = useState<LtaStatus | null>(null);
  const [transport, setTransport] = useState<TransportNetworkSummary | null>(null);
  const [forecast, setForecast] = useState<ForecastSnapshot | null>(null);
  const [feedState, setFeedState] = useState("Connecting");
  const [stopQuery, setStopQuery] = useState("");
  const [stopResults, setStopResults] = useState<BusStop[]>([]);
  const [arrivalBoard, setArrivalBoard] = useState<BusArrivalBoard | null>(null);
  const [transportMessage, setTransportMessage] = useState(
    "Search by stop code, road, or landmark.",
  );
  const [transportBusy, setTransportBusy] = useState(false);

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      const [nextWeather, nextAirQuality, nextLta, nextTransport, nextForecast] = await Promise.all([
        getWeather(),
        getAirQuality(),
        getLtaStatus(),
        getTransportNetwork(),
        getForecast(),
      ]);
      if (!active) return;
      setWeather(nextWeather);
      setAirQuality(nextAirQuality);
      setLta(nextLta);
      setTransport(nextTransport);
      setForecast(nextForecast);
      setFeedState(nextWeather || nextAirQuality || nextTransport ? "Live" : "Feed unavailable");
    };
    void refresh();
    const interval = window.setInterval(refresh, 5 * 60 * 1000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);
  const forecastGroups = Object.entries(
    (weather?.forecasts ?? []).reduce<Record<string, number>>((groups, item) => {
      groups[item.forecast] = (groups[item.forecast] ?? 0) + 1;
      return groups;
    }, {}),
  ).sort((a, b) => b[1] - a[1]);
  const primaryCondition = forecastGroups[0]?.[0] ?? "Feed unavailable";
  const transportAvailable = Boolean(transport && lta?.configured);

  const handleStopSearch = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = stopQuery.trim();
    if (query.length < 2 || !transportAvailable) return;
    setTransportBusy(true);
    setArrivalBoard(null);
    setTransportMessage("Searching the LTA stop directory…");
    const result = await searchBusStops(query);
    setStopResults(result?.stops ?? []);
    setTransportMessage(
      result?.stops.length
        ? `${result.stops.length} matching stop${result.stops.length === 1 ? "" : "s"}`
        : "No matching bus stops found.",
    );
    setTransportBusy(false);
  };

  const selectStop = async (stop: BusStop) => {
    setTransportBusy(true);
    setTransportMessage(`Loading live arrivals for ${stop.description || stop.road_name}…`);
    const board = await getBusArrivals(stop.code);
    setArrivalBoard(board);
    setTransportMessage(
      board
        ? `Updated ${formatTime(board.fetched_at)} from LTA DataMall`
        : "Live arrivals are temporarily unavailable.",
    );
    setTransportBusy(false);
  };

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="FluxSG home">
          <span className="brand-mark">F</span>
          <span>FluxSG</span>
        </a>
        <span className="system-state"><i /> Milestone 05 · {feedState}</span>
      </header>

      <section className="hero" id="top">
        <div>
          <p className="eyebrow">Singapore movement intelligence</p>
          <h1>Know the flow.<br /><em>Trust the signal.</em></h1>
          <p className="lede">
            A production-minded data platform connecting mobility, weather,
            quality, and forecasting evidence in one operational view.
          </p>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <strong>SG</strong>
        </div>
      </section>

      <section className="metric-grid" aria-label="Live platform metrics">
        <article className="metric feature">
          <span className="metric-label">Island outlook</span>
          <strong>{primaryCondition}</strong>
          <p>Valid until {formatTime(weather?.valid_to)}</p>
        </article>
        <article className="metric">
          <span className="metric-label">Areas observed</span>
          <strong>{weather?.forecasts.length ?? "—"}</strong>
          <p>Normalised locations</p>
        </article>
        <article className="metric">
          <span className="metric-label">Completeness</span>
          <strong>{weather ? `${weather.quality.completeness_percent}%` : "—"}</strong>
          <p>{weather?.quality.status ?? "Source offline"}</p>
        </article>
        <article className="metric">
          <span className="metric-label">Transport data</span>
          <strong className="small-value">
            {transport ? `${transport.bus_stop_count.toLocaleString("en-SG")} stops` : "Secured API"}
          </strong>
          <p>
            {transport
              ? `${transport.service_count} services · ${transport.route_pattern_count} patterns`
              : lta?.next_step ?? "Credential stays server-side"}
          </p>
        </article>
      </section>

      <section className="transit-console" aria-labelledby="transit-title">
        <div className="transit-intro">
          <p className="eyebrow">Live LTA movement layer</p>
          <h2 id="transit-title">Find a stop. Read the next three buses.</h2>
          <p>
            Search the official stop directory, then inspect live arrivals, crowding,
            vehicle type, and wheelchair accessibility without exposing the AccountKey.
          </p>
          <div className="network-proof" aria-label="LTA network summary">
            <div><strong>{transport?.bus_stop_count.toLocaleString("en-SG") ?? "—"}</strong><span>bus stops</span></div>
            <div><strong>{transport?.service_count ?? "—"}</strong><span>services</span></div>
            <div><strong>{transport?.quality.completeness_percent ?? "—"}%</strong><span>validated</span></div>
          </div>
        </div>
        <div className="arrival-tool">
          <form className="stop-search" onSubmit={handleStopSearch}>
            <label htmlFor="stop-query">Bus stop, road, or landmark</label>
            <div>
              <input
                id="stop-query"
                value={stopQuery}
                onChange={(event) => setStopQuery(event.target.value)}
                placeholder="Try 01012 or Raffles"
                minLength={2}
                disabled={!transportAvailable}
              />
              <button type="submit" disabled={!transportAvailable || transportBusy || stopQuery.trim().length < 2}>
                {transportBusy ? "Loading" : "Search"}
              </button>
            </div>
          </form>
          {!transportAvailable && (
            <p className="secure-note">
              The public preview keeps the LTA credential private. Run the secured API build
              locally to activate stop search and live arrivals.
            </p>
          )}
          <p className="tool-status" aria-live="polite">{transportMessage}</p>
          {stopResults.length > 0 && !arrivalBoard && (
            <div className="stop-results">
              {stopResults.map((stop) => (
                <button type="button" key={stop.code} onClick={() => void selectStop(stop)}>
                  <span><strong>{stop.code}</strong>{stop.description || "Unnamed stop"}</span>
                  <small>{stop.road_name}</small>
                </button>
              ))}
            </div>
          )}
          {arrivalBoard && (
            <div className="arrival-board">
              <div className="arrival-heading">
                <div><span>{arrivalBoard.bus_stop.code}</span><strong>{arrivalBoard.bus_stop.description}</strong></div>
                <button type="button" onClick={() => setArrivalBoard(null)}>Change stop</button>
              </div>
              <div className="service-list">
                {arrivalBoard.services.map((service) => (
                  <article key={service.service_no}>
                    <div className="service-number">{service.service_no}</div>
                    <div className="arrival-times">
                      {service.arrivals.length ? service.arrivals.map((arrival) => (
                        <div key={arrival.estimated_arrival} className={`load-${arrival.load?.toLowerCase() ?? "unknown"}`}>
                          <strong>{arrival.display}</strong>
                          <span>{arrival.load_label}</span>
                          <small>{arrival.vehicle_type}{arrival.wheelchair_accessible ? " · WAB" : ""}</small>
                        </div>
                      )) : <span className="no-arrival">No estimate available</span>}
                    </div>
                  </article>
                ))}
                {!arrivalBoard.services.length && <p className="no-arrival">No buses are currently reported at this stop.</p>}
              </div>
            </div>
          )}
        </div>
      </section>

      <section
        className={`haze-alert ${airQuality?.haze_alert ? "active" : "clear"}`}
        aria-labelledby="haze-title"
      >
        <div className="haze-score">
          <span>24-hour PSI</span>
          <strong>{airQuality?.national_psi ?? "—"}</strong>
          <em>{airQuality?.national_level ?? "Feed unavailable"}</em>
        </div>
        <div className="haze-copy">
          <p className="eyebrow">Citizen haze watch · Official regional readings</p>
          <h2 id="haze-title">
            {airQuality?.haze_alert
              ? "Haze alert: make the air part of today’s plan."
              : "Air-quality watch across all five regions."}
          </h2>
          <p>{airQuality?.guidance.general_population ?? "Start the API to load current guidance."}</p>
          {airQuality && (
            <p className="sensitive-note">
              <strong>Sensitive groups:</strong> {airQuality.guidance.sensitive_groups}
            </p>
          )}
          <div className="haze-meta">
            <span>Observed {formatTime(airQuality?.observed_at)}</span>
            <span>{airQuality?.quality.completeness_percent ?? "—"}% complete</span>
            <a href="https://www.haze.gov.sg/" target="_blank" rel="noreferrer">
              Official haze guidance ↗
            </a>
          </div>
        </div>
      </section>

      <section className="region-section" aria-labelledby="regions-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Your part of Singapore</p>
            <h2 id="regions-title">Regional air-quality check</h2>
          </div>
          <p>PSI uses a 24-hour average. PM2.5 1h shows the more immediate particle reading.</p>
        </div>
        <div className="region-grid">
          {(airQuality?.regions ?? []).map((region) => (
            <article className={`region-card level-${region.level.toLowerCase().replaceAll(" ", "-")}`} key={region.region}>
              <div className="region-name">
                <span>{region.region}</span>
                <i aria-label={`${region.level} air quality`} />
              </div>
              <strong>{region.psi_24h}</strong>
              <span className="region-level">{region.level}</span>
              <dl>
                <div><dt>PM2.5 · 1h</dt><dd>{region.pm25_1h}</dd></div>
                <div><dt>PM2.5 · 24h</dt><dd>{region.pm25_24h}</dd></div>
              </dl>
            </article>
          ))}
          {!airQuality && <div className="empty-state">Air-quality feed is currently unavailable.</div>}
        </div>
        <p className="health-disclaimer">
          {airQuality?.guidance.disclaimer ?? "General information only. Follow official health advice."}
        </p>
      </section>

      <section className="forecast-section" aria-labelledby="forecast-title">
        <div className="forecast-heading">
          <div>
            <p className="eyebrow">Guarded one-hour outlook</p>
            <h2 id="forecast-title">A forecast that can say “do not publish.”</h2>
          </div>
          <span className={`forecast-state ${forecast?.available ? "ready" : "withheld"}`}>
            {forecast?.available ? "Released" : "Withheld"}
          </span>
        </div>
        <p className="forecast-reason">
          {forecast?.reason ?? "The forecast publication manifest is currently unavailable."}
        </p>

        {forecast?.available ? (
          <div className="forecast-grid">
            {forecast.forecasts.map((item) => (
              <article key={item.region}>
                <span>{item.region}</span>
                <strong>{item.predicted_psi_24h}</strong>
                <em>{item.predicted_band}</em>
                <small>90% interval {item.lower_90}–{item.upper_90}</small>
              </article>
            ))}
          </div>
        ) : (
          <div className="guardrail-grid">
            {Object.entries(forecast?.checks ?? {}).map(([check, passed]) => (
              <div className={passed ? "passed" : "failed"} key={check}>
                <i aria-hidden="true" />
                <span>{check.replaceAll("_", " ")}</span>
                <strong>{passed ? "Pass" : "Block"}</strong>
              </div>
            ))}
            {!forecast && <div className="forecast-empty">No forecast evidence is available yet.</div>}
          </div>
        )}

        {forecast && (
          <div className="forecast-evidence">
            <div><span>Model test MAE</span><strong>{forecast.model.test_mae}</strong></div>
            <div><span>Persistence MAE</span><strong>{forecast.model.persistence_mae}</strong></div>
            <div><span>Interval coverage</span><strong>{Math.round(forecast.model.interval_coverage * 100)}%</strong></div>
            <div><span>Backtest wins</span><strong>{forecast.model.backtest_wins}/{forecast.model.backtest_folds}</strong></div>
            <div><span>Drift state</span><strong>{forecast.drift.status ?? "unknown"}</strong></div>
            <div><span>Forecast time</span><strong>{formatTime(forecast.forecast_for)}</strong></div>
          </div>
        )}
        <p className="forecast-disclaimer">
          {forecast?.disclaimer ?? "Experimental estimate only. Follow official NEA observations and haze guidance."}
        </p>
      </section>

      <section className="content-grid">
        <article className="panel conditions">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Live distribution</p>
              <h2>Conditions across Singapore</h2>
            </div>
            <span className={`quality ${weather?.quality.status ?? "offline"}`}>
              {weather?.quality.status ?? "offline"}
            </span>
          </div>
          {forecastGroups.length > 0 ? (
            <div className="condition-list">
              {forecastGroups.slice(0, 6).map(([condition, count]) => (
                <div className="condition-row" key={condition}>
                  <span>{condition}</span>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{ width: `${Math.max(8, (count / (weather?.forecasts.length ?? 1)) * 100)}%` }}
                    />
                  </div>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              Start the FluxSG API to load the live data.gov.sg forecast.
            </div>
          )}
        </article>

        <aside className="panel source-card">
          <p className="eyebrow">Data trust</p>
          <h2>Every number carries evidence.</h2>
          <dl>
            <div><dt>Provider</dt><dd>{weather?.source ?? "data.gov.sg / NEA"}</dd></div>
            <div><dt>Source update</dt><dd>{formatTime(weather?.source_updated_at)}</dd></div>
            <div><dt>FluxSG ingest</dt><dd>{formatTime(weather?.ingested_at)}</dd></div>
            <div><dt>Rejected rows</dt><dd>{weather ? weather.quality.received_records - weather.quality.valid_records : "—"}</dd></div>
          </dl>
        </aside>
      </section>

      <footer>
        <span>FluxSG · Built by Hnin Phyu Phyu Aye</span>
        <span>Not an official government service</span>
      </footer>
    </main>
  );
}
