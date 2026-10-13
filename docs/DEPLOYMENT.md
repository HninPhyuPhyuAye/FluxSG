# Deployment

## Public dashboard

GitHub Pages builds the static Next.js export from `.github/workflows/pages.yml`.
The repository variable `FLUXSG_API_URL` is compiled into the browser bundle as
`NEXT_PUBLIC_FLUXSG_API_URL`. When the variable is absent, the dashboard uses
only the credential-free data.gov.sg fallback.

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

The production CORS value is:

```text
https://hninphyuphyuaye.github.io
```

The LTA key must be entered through Vercel's secret interface or CLI. It must
never be copied into `vercel.json`, GitHub Actions variables, or source code.

Production verification checklist:

1. `/health` returns `status: ok`.
2. `/api/v1/integrations/lta` reports `configured: true`.
3. The network, stop-search, arrival, and route endpoints return validated LTA
   data.
4. The GitHub repository variable `FLUXSG_API_URL` points to the production API.
5. The public dashboard can search for `Raffles` and load live arrivals for
   Raffles Hotel (`02049`).
