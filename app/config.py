from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = "Monitoring API"
    version: str = "1.0"
    debug: bool = True

    # БД SQLite (async)
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./monitoring.db",
    )

settings = Settings()