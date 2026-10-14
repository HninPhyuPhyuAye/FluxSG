# Production cost report

## Current portfolio deployment

The current recurring cash cost is **SGD 0 per month**, subject to provider
fair-use rules and included limits. This is a measured architecture decision,
not a claim of unlimited free capacity.

| Component | Current plan | Expected cash cost | Capacity boundary |
|---|---|---:|---|
| Static dashboard and hourly forecast build | GitHub Pages + Actions, public repository | SGD 0 | Standard GitHub-hosted runners are free for public repositories; artifact storage remains quota-limited |
| FastAPI functions | Vercel Hobby | SGD 0 | 1,000,000 function invocations, 4 active CPU-hours, and 360 GB-hours provisioned memory included monthly |
| Live NEA data | data.gov.sg public API | SGD 0 | Production key recommended for higher rate limits |
| LTA transport data | LTA DataMall account key | SGD 0 | Subject to the provider's account and fair-use terms |
| Local observability and storage | Docker Desktop on developer machine | Existing hardware | Not a highly available production database |

Official references: [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[Vercel Hobby limits](https://vercel.com/docs/plans/hobby), and
[data.gov.sg API limits](https://guide.data.gov.sg/developer-guide/api-overview/api-rate-limits).

## Scaling decision

The first paid trigger should be reliability, not vanity traffic. Upgrade or
re-platform when any of these becomes true:

- the API approaches 70% of an included Vercel resource limit;
- scheduled builds regularly exceed the provider's execution window;
- historical data must be retained outside the developer machine;
- restore time, multi-region availability, or alert delivery becomes a formal
  business requirement;
- the project becomes commercial, which is outside Vercel Hobby's intended
  personal-project use.

A serious production version should budget separately for a managed PostgreSQL
database with point-in-time recovery, durable object storage, managed metrics,
alert delivery, and a Vercel Pro or equivalent compute plan. Exact prices are
region- and usage-dependent, so FluxSG records consumption before selecting a
paid configuration instead of presenting a misleading fixed estimate.

## Cost controls

- Static files serve citizen traffic without invoking the API.
- The API proxies a small release-gated JSON contract instead of loading
  scikit-learn in every function invocation.
- Forecast generation is bounded to one hourly build and nine recent API days.
- LTA network metadata is cached for six hours.
- Forecast evidence artifacts expire after 30 days.
- Alerts should be added at 50%, 70%, and 90% of any paid provider budget before
  enabling on-demand spend.
