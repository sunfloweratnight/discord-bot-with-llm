from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DISCORD_API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    # Overridable so Koyeb can switch models without a code change.
    GEMINI_MODEL: str = "gemini-3.5-flash"
    INITIAL_PROMPT: str
    # TypeSafe Jev (運勢). Optional so the bot can boot without it; Fortune cog checks at runtime.
    TYPESAFE_API_KEY: str = ""
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

    def get_db_url(self):
        return None


settings = Settings()
