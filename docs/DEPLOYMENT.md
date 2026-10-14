# Deployment

## Public dashboard

GitHub Pages builds the static Next.js export from `.github/workflows/pages.yml`.
The repository variable `FLUXSG_API_URL` is compiled into the browser bundle as
`NEXT_PUBLIC_FLUXSG_API_URL`. When the variable is absent, the dashboard uses
only the credential-free data.gov.sg fallback.

The same workflow runs hourly. It retrains the PSI candidate with official
archive plus recent readings and publishes a freshness- and drift-gated
`data/forecast.json`. A failed forecast build leaves the previous deployment in
place; browser and API expiry checks then withhold it automatically.

- Dashboard: <https://hninphyuphyuaye.github.io/FluxSG/>
- Production API: <https://fluxsg-api.vercel.app>
- Interactive API docs: <https://fluxsg-api.vercel.app/docs>

## Secured API

The FastAPI service is deployed from `services/api` as a Vercel Python Function.
`services/api/vercel.json` gives the function enough time for a cold metadata
load while bounded pagination prevents an unbounded upstream request loop.

Required production environment variables:

| Variable | Visibility | Purpose |
| --- | --- | --- |
| `LTA_ACCOUNT_KEY` | Secret | Authenticates server-to-server LTA DataMall calls |
| `CORS_ORIGINS` | Config | Allows the GitHub Pages origin |
| `ENVIRONMENT` | Config | Identifies the production runtime |
| `FORECAST_MANIFEST_URL` | Config | Points the API at the guarded Pages artifact |

The production CORS value is:

```text
https://hninphyuphyuaye.github.io
```

The LTA key must be entered through Vercel's secret interface or CLI. It must
never be copied into `vercel.json`, GitHub Actions variables, or source code.

`infra/terraform` manages the non-secret GitHub environment variables and the
Vercel manifest URL. `LTA_ACCOUNT_KEY` and, when configured,
`DATA_GOV_SG_API_KEY` remain in their respective encrypted provider secret
stores.

Production verification checklist:

1. `/health` returns `status: ok`.
2. `/api/v1/integrations/lta` reports `configured: true`.
3. The network, stop-search, arrival, and route endpoints return validated LTA
   data.
4. The GitHub repository variable `FLUXSG_API_URL` points to the production API.
5. The public dashboard can search for `Raffles` and load live arrivals for
   Raffles Hotel (`02049`).
