# Haze Watch product decision

## Why this belongs in FluxSG

Weather, air quality, transport demand, and outdoor movement interact during a
haze episode. Haze Watch gives residents an immediately useful feature while
creating meaningful future data-engineering questions: whether unhealthy air
changes travel volumes, which regions are most affected, and how quickly
conditions change.

## Trust model

FluxSG leads with official NEA PSI and PM2.5 readings from data.gov.sg. A live
third-party world ranking is deliberately not used as the primary alert because
rank position can change minute by minute, methodologies differ, and a historic
"number one" claim becomes misleading after conditions improve.

The interface therefore shows:

- the highest current regional 24-hour PSI and its official severity band;
- all five regional PSI values rather than a single national average;
- one-hour and 24-hour PM2.5 readings for context;
- observation time, completeness, and source provenance;
- a direct link to official haze guidance;
- an explicit disclaimer that FluxSG is not a government or medical service.

## Citizen experience roadmap

1. Save a preferred region without requiring an account.
2. Optional browser notifications when that region crosses a chosen PSI level.
3. PWA support and a low-bandwidth status screen.
4. Multilingual summaries for English, Mandarin, Malay, and Tamil.
5. Accessible colour-independent severity labels and screen-reader testing.
6. Historical trends and transport-impact analysis after the warehouse exists.

Notification and location permissions will always be opt-in. FluxSG will not
collect precise location when a user can select one of five broad regions.

