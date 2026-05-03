from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_HOST: str = ""
    WEBHOOK_PATH: str = "/webhook"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_IMAGE_API_KEY: str = ""  # отдельный ключ для изображений, если не задан — используется OPENROUTER_API_KEY
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_TEXT_MODEL: str = "anthropic/claude-3.5-sonnet"
    DEFAULT_IMAGE_MODEL: str = "fal-ai/flux-pro"

    @property
    def effective_image_api_key(self) -> str:
        return self.OPENROUTER_IMAGE_API_KEY or self.OPENROUTER_API_KEY

    LOG_LEVEL: str = "INFO"
    MAX_CONCURRENT_IMAGE_TASKS: int = 5
    DB_PATH: str = "data/vibemaster.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
