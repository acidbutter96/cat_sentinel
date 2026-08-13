from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, env-driven via pydantic-settings.

    Every module that needs config imports `settings` from here -- never
    reads os.environ directly.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "cat-sentinel"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    log_dir: str = "logs"
    snapshot_dir: str = "snapshots"
    registered_cat_image_dir: str = "registered_cat_images"

    # Persistence -- SQLite for local dev, Postgres+asyncpg in production.
    database_url: str = "sqlite+aiosqlite:///./cat_sentinel.db"

    # Upstream camera / streaming
    camera_stream_url: str = "http://localhost:9000/video"
    camera_id: str = "default"

    # Alerts
    alert_webhook_url: str = "http://localhost:9100/webhooks/cat-sentinel"
    alert_cooldown_seconds: int = 60
    # Cooldown for "cat entered camera view" alerts, tracked separately from
    # danger-zone cooldown above so tuning one doesn't affect the other.
    alert_entry_cooldown_seconds: int = 30

    # Vision / detection pipeline
    yolo_model_path: str = "yolov8n.pt"
    yolo_confidence_threshold: float = 0.5
    centroid_max_distance: float = 75.0
    centroid_max_age_frames: int = 30

    # Re-identification: minimum cosine similarity between a new observation's
    # appearance embedding and a stored cat's embedding to treat them as the
    # same cat rather than creating a new identity. See app.vision.reid and
    # app.cats.service.CatService.identify_or_create.
    reid_similarity_threshold: float = 0.7

    # Pipeline control
    detection_pipeline_enabled: bool = True
    detection_frame_interval_seconds: float = 0.2


settings = Settings()
