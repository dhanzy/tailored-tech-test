from cache_service.config import ServiceSettings


def _settings(**kwargs) -> ServiceSettings:
    # _env_file=None keeps a developer's real .env out of the tests.
    return ServiceSettings(_env_file=None, **kwargs)


def test_defaults_to_sqlite():
    assert _settings().sqlalchemy_url == "sqlite:///./cache.db"


def test_builds_postgres_url_and_escapes_password():
    url = _settings(postgres_host="db", postgres_password="p@ss/word").sqlalchemy_url
    assert url == "postgresql+psycopg://postgres:p%40ss%2Fword@db:5432/cache"


def test_explicit_database_url_wins():
    assert _settings(database_url="sqlite:///x.db", postgres_host="db").sqlalchemy_url == (
        "sqlite:///x.db"
    )


def test_reads_dotenv_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("CACHE_POSTGRES_HOST=fromfile\n")
    assert "fromfile" in ServiceSettings(_env_file=env).sqlalchemy_url
