from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegionalPsiForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    region: str
    observed_psi_24h: float = Field(ge=0)
    predicted_psi_24h: float = Field(ge=0)
    lower_90: float = Field(ge=0)
    upper_90: float = Field(ge=0)
    predicted_band: str


class ForecastModelSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    trained_through: datetime
    age_hours: float = Field(ge=0)
    test_mae: float = Field(ge=0)
    persistence_mae: float = Field(ge=0)
    interval_coverage: float = Field(ge=0, le=1)
    backtest_wins: int = Field(ge=0)
    backtest_folds: int = Field(ge=0)


class ForecastManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    forecast_type: str
    source: str
    source_url: str
    generated_at: datetime
    observed_at: datetime
    forecast_for: datetime
    expires_at: datetime
    available: bool
    status: str
    reason: str
    checks: dict[str, bool]
    freshness_hours: float = Field(ge=0)
    model: ForecastModelSummary
    drift: dict[str, object]
    forecasts: list[RegionalPsiForecast]
    disclaimer: str
