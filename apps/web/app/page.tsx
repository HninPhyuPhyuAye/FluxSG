import { getAirQuality, getLtaStatus, getWeather } from "@/lib/api";
import { connection } from "next/server";

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

export default async function Home() {
  // Live operational readings must be resolved inside the running environment,
  // not frozen into the image during `next build`.
  await connection();
  const [weather, airQuality, lta] = await Promise.all([
    getWeather(),
    getAirQuality(),
    getLtaStatus(),
  ]);
  const forecastGroups = Object.entries(
    (weather?.forecasts ?? []).reduce<Record<string, number>>((groups, item) => {
      groups[item.forecast] = (groups[item.forecast] ?? 0) + 1;
      return groups;
    }, {}),
  ).sort((a, b) => b[1] - a[1]);
  const primaryCondition = forecastGroups[0]?.[0] ?? "Feed unavailable";

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="FluxSG home">
          <span className="brand-mark">F</span>
          <span>FluxSG</span>
        </a>
        <span className="system-state"><i /> Milestone 01 · Live</span>
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
          <span className="metric-label">LTA integration</span>
          <strong className="small-value">{lta?.configured ? "Ready" : "Key needed"}</strong>
          <p>{lta?.next_step ?? "API unavailable"}</p>
        </article>
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

