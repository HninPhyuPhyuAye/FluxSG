from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import air_quality, system, transport, weather
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    summary="Trusted Singapore mobility and environmental data",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(system.router)
app.include_router(weather.router)
app.include_router(air_quality.router)
app.include_router(transport.router)

