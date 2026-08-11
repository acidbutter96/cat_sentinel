"""Central, env-driven application configuration.

Every module that needs configuration imports `settings` from here -- never
reads `os.environ` directly. Values are overridable via a `.env` file or real
environment variables (real env vars win).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Camera connection (TP-Link Tapo C200) ---
    # RTSP/ONVIF stream credentials: the *local* "Camera Account" set in the
    # Tapo app under Advanced Settings > Camera Account -- NOT the TP-Link
    # cloud account used below for PTZ control.
    camera_host: str = "192.168.1.50"
    camera_rtsp_port: int = 554
    camera_rtsp_user: str = "admin"
    camera_rtsp_password: str = "changeme"
    # /stream1 = HD (main, higher bitrate), /stream2 = SD (sub, lower
    # bitrate/lower latency) -- the two profiles the C200 exposes.
    camera_rtsp_path: str = "/stream1"
    camera_rtsp_transport: str = "tcp"  # "tcp" or "udp"

    @property
    def camera_rtsp_url(self) -> str:
        return (
            f"rtsp://{self.camera_rtsp_user}:{self.camera_rtsp_password}@"
            f"{self.camera_host}:{self.camera_rtsp_port}{self.camera_rtsp_path}"
        )

    # --- PTZ control (pytapo) ---
    # Separate credential set from the RTSP ones above: this is the
    # TP-Link cloud account email/password (or, on some firmware, the same
    # local "Camera Account") that pytapo authenticates with to drive the
    # pan/tilt motor -- see app/ptz/service.py.
    tapo_control_user: str = ""
    tapo_control_password: str = ""
    # Empirical conversion factor between pytapo's moveMotor(x, y)
    # coordinate units and degrees -- Tapo does not document or guarantee
    # this, so re-tune it by testing on your own unit. See the caveat in
    # app/ptz/service.py's module docstring.
    ptz_units_per_degree: float = 10.0

    # --- HTTP server ---
    http_port: int = 8000

    # --- Events / webhooks ---
    events_api_key: str | None = None
    webhook_timeout_seconds: float = 3.0

    # --- Recordings ---
    recording_scan_interval_seconds: int = 300
    recordings_dir: str = "./recordings"

    # --- Database (Postgres for recordings) ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jortan_camera"

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
