"""Application configuration (loaded from environment in later steps)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SKYFOCUS_")

    app_name: str = "SkyFocus API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # External data sources
    opensky_base_url: str = "https://opensky-network.org/api"
    use_mock_adsb: bool = False
    adsb_poll_interval_sec: float = 10.0
    metar_poll_interval_sec: float = 300.0
    telemetry_window_sec: float = 600.0
    ws_broadcast_interval_sec: float = 2.0


settings = Settings()
