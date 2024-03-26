from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DISCORD_API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    POSTGRES_HOSTNAME: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_INTERNAL_URL: str
    POSTGRES_EXTERNAL_URL: str
    IS_PROD: bool

    class Config:
        env_file = ".env"

    def get_db_url(self):
        return self.IS_PROD and self.POSTGRES_INTERNAL_URL or self.POSTGRES_EXTERNAL_URL


settings = Settings()
