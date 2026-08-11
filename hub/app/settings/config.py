from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-driven settings for the hub aggregator service.

    hub has no database of its own -- these settings are entirely about how
    to reach the upstream services it aggregates, and how it presents itself.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Upstream services. Defaults follow the "900x" dev scheme; some dev
    # environments run cat-sentinel on 8002 and camera on 8001 instead --
    # override via env vars in that case.
    cat_sentinel_base_url: str = "http://localhost:9001"
    camera_base_url: str = "http://localhost:9000"

    # Timeout (seconds) for normal control-plane calls to upstream services
    # (e.g. GET /cats/, GET /detections/). Deliberately NOT used for the
    # MJPEG stream proxy -- see core/dependencies.py.
    upstream_control_timeout: float = 10.0

    # hub's own bind port. Default 8000; some dev schemes use 9002.
    hub_port: int = 8000

    debug: bool = False
    log_level: str = "INFO"


settings = Settings()
