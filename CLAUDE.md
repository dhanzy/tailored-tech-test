# CLAUDE.md

Take-home for a Python backend role. Spec is in `Test Task Python.md`. FastAPI caching service plus a small CLI.
I have to walk through this on video and change it live in the interview, so I need to understand every line.
Keep things simple. If something looks clever, make it plainer.

## Tooling

uv for everything. No pip, no requirements.txt.

    uv sync                                    # install
    uv run pytest                              # tests
    uv run ruff check . && uv run ruff format .
    uv run uvicorn cache_service.main:app --reload
    uv run cache-cli --help
    docker build -t cache-service .

If the editable install breaks: `uv sync --reinstall-package cache-service`.

## How it fits together

Request path is api.py -> service.py -> models.py -> DB.

- `api.py` - routes and dependencies only, no logic. Endpoints are plain `def` on purpose (blocking DB calls).
- `service.py` - the actual caching. Read this one first.
- `transformer.py` - fake external service (uppercase). Treat every call as expensive.
- `config.py` - settings from `CACHE_*` env vars / `.env`. Postgres if `CACHE_POSTGRES_HOST` is set, else SQLite.
- `cli.py` - `cache-cli`. Uses its own ArgumentParser so `-h` can be `--host`; help is `--help`.

## Decisions I made (be ready to explain these)

- Payload id is a sha256 of the JSON-encoded input, so the same input always gives the same id.
- Transformed values are cached per unique string, not per payload. Only misses call the transformer.
- A lost insert race is fine: rows are the same for the same key, so catch IntegrityError and merge.
- Transformer is a FastAPI dependency so tests can swap in a fake that counts calls.
- Logs only counts of hits/misses, never the strings (could be user data).
- Known shortcuts (also in README): no migrations, `", "` separator is ambiguous if strings contain commas,
  no lock around the transformer.

## Rules for this repo

- Fewest possible transformer calls. Never call it for something already cached or repeated in one request.
- No `print()` in `src/`. Use `logging`. The CLI writes JSON to stdout and anything else there breaks it.
- Comments say why, not what.
- New behaviour gets a test. Use the counting transformer fixture in `tests/conftest.py`.
- Tests must not touch my real `.env` or database (use tmp_path / `_env_file=None`).
- `ruff` and `pytest` both pass before I call anything done.
- Never commit `.env`, `*.db`, `.venv`. `.env.example` is the one that gets committed.
- Don't commit unless I ask. When I do: small commits, clear messages, no squashing, history is graded.
- Repo name must be neutral, no company name anywhere in it.
- Don't say something works unless it was actually run.

## Still to do

- Public repo, video walkthrough (max 15 min), reply with hours spent.
- Decide whether to add a postgres service to docker-compose.

## Notes to self

- Postgres database has to exist already (`createdb cache`); the app only creates tables.
- Task says `-h` for both host and help. Chose host, mention it in the video.
