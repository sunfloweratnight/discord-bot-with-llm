from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DISCORD_API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    # COHERE_API_KEY: str
    # POSTGRES_HOSTNAME: str
    # POSTGRES_PORT: str
    # POSTGRES_DB: str
    # POSTGRES_USER: str
    # POSTGRES_PASSWORD: str
    # POSTGRES_INTERNAL_URL: str
    # POSTGRES_EXTERNAL_URL: str
    # IS_PROD: bool

    LOG_CHANNEL_ID: int
    GAKUBUCHI_CHANNEL_ID: int
    MINNA_BUNKO_CHANNEL_ID: int
    FREEMEMO_CHANNEL_ID: int
    GUILD_ID: int

    class Config:
        env_file = ".env"

    def get_db_url(self):
        return None


settings = Settings()
