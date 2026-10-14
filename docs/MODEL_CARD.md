# Model card: regional PSI one-hour forecast

## Status

**Promoted for experimental evaluation, not public-health or production use.**

The candidate passed the offline promotion rule on the 2023–2024 archive. The
held-out period also triggered a pollutant-distribution drift alert, and the
training archive ends in 2024. FluxSG therefore does not display this forecast
as current citizen guidance. Recent-history retraining and production monitoring
remain required before public release.

## Production release check · 14 October 2026

The Milestone 5 publisher added nine days of current readings and refitted the
serving artifact through 14 October 2026. Freshness and regional-completeness
checks passed, but the operational release was **withheld**:

| Production check | Result | Decision |
|---|---:|---|
| Candidate holdout MAE | 3.6072 | Failed against persistence |
| Persistence holdout MAE | **0.6504** | Stronger baseline |
| Nominal 90% interval coverage | 81.54% | Failed 85% release floor |
| Recent distribution drift | Alert | Failed |
| Source freshness | 0.72 hours | Passed |
| Model age | 1.72 hours | Passed |

This result demonstrates why retraining alone is not a safety argument. The
current haze period is materially different from the old training distribution,
and the simple persistence forecast is much stronger. FluxSG therefore hides
the model estimates from the citizen view while continuing to show official NEA
observations and the failed release checks.

## Intended use

The model estimates each Singapore region's 24-hour PSI one hour ahead. It is an
engineering and data-science demonstration for comparing short-horizon trends
and deciding whether a candidate deserves further operational testing.

It must not be used for medical decisions, school/workplace policy, emergency
response, or as a substitute for NEA and haze.gov.sg observations and advice.

## Training data

- Official hourly regional NEA PSI history for 2023 and 2024
- 82,465 labelled regional examples after hourly alignment and lag creation
- Five regions; national aggregate rows excluded
- Training: 57,725 rows, 11 January 2023–7 June 2024 SGT
- Validation: 12,370 rows, 7 June–19 September 2024 SGT
- Test: 12,370 rows, 19 September–31 December 2024 SGT

The source archive documents possible missing records. FluxSG reindexes each
region hourly and allows missing-value-aware modelling; it does not interpolate
the prediction target across missing periods.

## Results

| Model | Validation MAE | Test MAE | Test RMSE | Test PSI-band accuracy |
|---|---:|---:|---:|---:|
| Candidate gradient boosting | **0.5580** | **0.5867** | **0.8133** | **98.09%** |
| Persistence | 0.5615 | 0.5991 | 0.9401 | 97.88% |
| 24-hour seasonal | 7.2027 | 7.2773 | 9.5396 | 74.14% |

The candidate improved validation MAE over the strongest baseline by only
**0.62%**. That is a real but small gain and should not be described as a large
breakthrough. It beat persistence in three of four expanding-window backtests;
the first fold was worse, showing that performance varies by period.

The validation-calibrated nominal 90% interval had a radius of 1.1988 PSI and
achieved 88.93% test coverage with a mean width of 2.3976 PSI. It is close to,
but below, nominal coverage and needs recalibration before operational use.

## Drift result

The untouched test period raised an overall **alert**:

| Feature | Population stability index | Status |
|---|---:|---|
| 24-hour PSI | 0.2456 | Warning |
| 24-hour PM2.5 | 0.2655 | Alert |
| 24-hour PM10 | 0.0792 | Healthy |
| Eight-hour ozone | 0.0955 | Healthy |

Here “population stability index” is the statistical drift metric, not
Singapore's Pollutant Standards Index. A drift alert asks for investigation and
retraining; it does not claim that air quality is hazardous.

## Important limitations

- The target is a rolling 24-hour PSI measure, so persistence is naturally very
  strong and abrupt one-hour pollution spikes can be masked.
- The model has pollutant history and time features but no wind, rainfall,
  hotspot, fire, or transboundary-plume forecast inputs.
- The archive ends in 2024, so the serialized model must not be treated as a
  current 2026 production model.
- Band accuracy is dominated by common Good/Moderate observations and does not
  establish reliable performance during rare severe haze.
- Regional readings are not street-level exposure measurements.
- The interval is empirical and does not guarantee coverage during novel haze
  events or major source changes.

## Release requirements

Before citizen-facing deployment:

1. ingest sufficient recent hourly observations and rerun the same locked test;
2. investigate and clear or explicitly accept drift alerts;
3. evaluate rare Unhealthy-or-worse periods separately;
4. add weather and wind features only if they are available at prediction time;
5. monitor realised error, interval coverage, freshness, and missing regions;
6. label every forecast as an estimate beside current official observations.

## Reproducibility

The deterministic training seed is 42. The pipeline pins Python package
versions, stores input checksums and chronological boundaries, and writes
row-level held-out predictions. Run `make forecast` to reproduce the experiment
and inspect `ml/artifacts/latest/metrics.json` for the latest machine-readable
record. The verified Milestone 4 result is committed at
[`ml/reports/reference_metrics.json`](../ml/reports/reference_metrics.json).
