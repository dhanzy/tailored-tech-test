# cache-service

FastAPI microservice that builds payloads by transforming two string lists and interleaving the results,
caching transformer output in SQLite so the (simulated) external service is called as rarely as possible.

## Run

```bash
uv sync
uv run uvicorn cache_service.main:app          # http://localhost:8000/docs
# or
docker compose up --build                       # DB persisted in a volume
```

Config: `CACHE_DATABASE_URL` (any SQLAlchemy URL, default `sqlite:///./cache.db`).

## API

| Method | Path | Result |
|---|---|---|
| POST | `/payload` | `201 {"id", "message"}`; body `{"list_1": [...], "list_2": [...]}` (equal length, else 422) |
| GET | `/payload/{id}` | `{"output": "FIRST STRING, OTHER STRING, ..."}` or 404 |

## CLI

`cache-cli` is declared under `[project.scripts]` in `pyproject.toml`. `uv sync` installs the project in editable
mode and generates the launcher at `.venv/bin/cache-cli`, so there is no separate build step. Run it with
`uv run cache-cli`, or activate the venv (`source .venv/bin/activate`) and call `cache-cli` directly.

```bash
# start the server in another terminal first: uv run uvicorn cache_service.main:app
uv run cache-cli -h http://localhost:8000 -r 2 \
  -j '{"list_1":["first string","second string"],"list_2":["other string","another string"]}'
```

Output (one line per iteration; the same id both times shows the second request was served from cache):

```json
{"id": "895bfbf43e9fb4136471876707977715e4a8f4bc570551c77fc7475ac38b2bbf", "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"}
{"id": "895bfbf43e9fb4136471876707977715e4a8f4bc570551c77fc7475ac38b2bbf", "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"}
```

Other input forms:

```bash
echo '{"list_1":["a"],"list_2":["b"]}' | uv run cache-cli -i -      # stdin
uv run cache-cli -i payload.json -o result.jsonl                      # files
```

Flags: `-h/--host`, `-r/--repeat`, `-i/--input FILE|-`, `-j/--json`, `-o/--output FILE|-`, `--help`.
Exactly one of `--input`/`--json`. Each iteration POSTs then GETs and prints a `{"id","output"}` JSON line;
repeating is a quick check that the same id is returned.

## Design

- **Payload id** = SHA-256 of the JSON-encoded input, so identical requests return the existing id without any work.
- **String cache**: each unique string's transformed value is stored once (`TransformedString`). A request
  only calls the transformer for strings missing from the cache, deduplicated within the request.
- **Concurrency**: rows are deterministic per key, so a lost insert race is tolerated rather than failing.
- Sync endpoints, because DB/transformer calls block; FastAPI runs them in a threadpool.

## Decisions and shortcuts

- The spec lists `-h` for both host and help; `-h` is host, help is `--help`.
- Joining with `", "` follows the sample output; strings containing commas are therefore ambiguous in the output.
- Transformer is `str.upper`, called per string (no batch API assumed).
- Tables are created at startup; no migrations (Alembic would be the next step).
- No lock around the transformer, so two concurrent identical new requests may each call it once.

## Tests

`uv run pytest` – API tests (caching, id reuse, validation, 404) and CLI tests, using a call-counting transformer.
