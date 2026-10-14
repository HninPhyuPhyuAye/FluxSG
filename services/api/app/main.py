from time import monotonic

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import air_quality, forecast, pipeline, system, transport, weather
from app.core.config import get_settings
from app.core.metrics import HTTP_DURATION, HTTP_REQUESTS
from app.core.observability import configure_tracing

settings = get_settings()
configure_tracing(settings.otel_service_name, settings.otel_exporter_otlp_endpoint)

app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    summary="Trusted Singapore mobility and environmental data",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observe_http(request: Request, call_next):  # type: ignore[no-untyped-def]
    started = monotonic()
    response = await call_next(request)
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    HTTP_REQUESTS.labels(request.method, route_path, str(response.status_code)).inc()
    HTTP_DURATION.labels(request.method, route_path).observe(monotonic() - started)
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(system.router)
app.include_router(weather.router)
app.include_router(air_quality.router)
app.include_router(forecast.router)
app.include_router(transport.router)
app.include_router(pipeline.router)
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/metrics")
