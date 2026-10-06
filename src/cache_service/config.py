from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class ServiceSettings(BaseSettings):
    """Server configuration, read from CACHE_* environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_prefix="CACHE_", env_file=".env", extra="ignore")

    # Escape hatch: a full SQLAlchemy URL wins over everything else.
    database_url: str | None = None

    # PostgreSQL is configured as separate parts (rather than one URL) so a
    # password containing characters like "@" or "/" needs no manual escaping.
    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("")
    postgres_db: str = "cache"

    @property
    def sqlalchemy_url(self) -> str:
        """Explicit URL, else PostgreSQL if a host is set, else a local SQLite file."""
        if self.database_url:
            return self.database_url
        if self.postgres_host:
            return URL.create(
                "postgresql+psycopg",
                username=self.postgres_user,
                password=self.postgres_password.get_secret_value(),
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
            ).render_as_string(hide_password=False)
        return "sqlite:///./cache.db"
