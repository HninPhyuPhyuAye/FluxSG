# Air-aware commute signal

FluxSG's commute endpoint combines live public-transport arrivals with current
official regional air-quality observations:

```text
GET /api/v1/commute/stops/{five-digit-stop-code}
```

The endpoint requests the LTA arrival board and NEA air snapshot concurrently,
maps the bus stop to the geographically nearest official reporting region, and
returns both the complete arrival board and an exposure assessment. This keeps
the LTA AccountKey in the backend and prevents the browser from coordinating
two partially successful source calls.

## Score contract

The score is a bounded planning signal, not a learned model or medical exposure
measurement. Every response includes the component values and a plain-language
explanation.

| Component | Weight | Calculation |
|---|---:|---|
| Regional 24-hour PSI | 55 | `min(psi / 300 × 55, 55)` |
| Regional PM2.5 1-hour reading | 30 | `min(pm25 / 250 × 30, 30)` |
| Shortest reported bus wait | 15 | `min(wait_minutes / 30 × 15, 15)` |

The rounded total is labelled `Low` below 25, `Elevated` from 25–49, `High`
from 50–74, and `Very high` from 75. If LTA reports no usable arrival estimate,
the wait component is zero and the explanation discloses that missing signal;
FluxSG does not invent an ETA.

## Interpretation limits

- NEA regions are broad reporting areas. Nearest-region mapping is an explicit
  approximation, not street-level pollution sensing.
- PSI is a 24-hour measure and PM2.5 1-hour is a short-term regional reading.
- The score does not know a person's health, indoor time, route, mask, or exact
  time spent outdoors.
- The score ranks the current stop-and-wait situation only. It is not a medical
  recommendation and does not replace NEA or haze.gov.sg guidance.
- Browser watch preferences remain in local storage. Browser notifications are
  requested only after the user presses the enable button and work while the
  dashboard is open; FluxSG stores no notification identity.

## Failure behaviour

Invalid stop codes are rejected before source access. A missing stop returns
404. A failure in either LTA or NEA returns 503 rather than calculating a score
from incomplete cross-domain evidence. Source-specific endpoints remain
available for diagnosis.
