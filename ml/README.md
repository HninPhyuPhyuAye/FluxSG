# FluxSG forecasting

This package trains and evaluates a one-hour-ahead regional 24-hour PSI model
using official historical NEA data from data.gov.sg.

The evaluation is deliberately chronological. It compares histogram gradient
boosting with both a 24-hour seasonal baseline and a harder persistence
baseline, calibrates a 90% residual interval on validation data, performs
expanding-window backtests, and refuses promotion unless the candidate beats
both baselines on validation MAE.

From the repository root:

```bash
make forecast-data
make forecast
make forecast-live
make forecast-drift
```

`forecast-live` fetches nine days of official hourly data, refits the model,
and writes a public-manifest candidate whose freshness, holdout performance,
interval coverage, and drift checks can withhold release.

Raw source files and fitted model artifacts stay local. Version-controlled
reference results and the complete limitations are in
[`docs/FORECASTING.md`](../docs/FORECASTING.md) and
[`docs/MODEL_CARD.md`](../docs/MODEL_CARD.md).
