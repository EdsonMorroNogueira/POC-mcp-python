from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_prefix": "NERD_TOOLKIT_"}

    scryfall_base_url: str = "https://api.scryfall.com"
    scryfall_rate_limit_ms: int = 100
    dnd_base_url: str = "https://www.dnd5eapi.co/api"
    request_timeout: int = 10
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 10.0
    log_level: str = "INFO"


settings = Settings()
