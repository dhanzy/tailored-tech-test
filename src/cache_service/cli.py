"""``cache-cli``: exercise the service from the command line."""

import argparse
import json
import sys
from pathlib import Path
from typing import Annotated, Self

import httpx
from pydantic import AnyHttpUrl, Field, ValidationError, model_validator
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliSettingsSource,
    SettingsConfigDict,
)

from cache_service.schemas import PayloadRequest


class CliSettings(BaseSettings):
    """Parsed and validated command line.

    ``-h`` is taken by ``--host`` as the task specifies (it also lists ``-h`` for
    help, which cannot work for both); help stays available as ``--help``.
    """

    model_config = SettingsConfigDict(
        cli_prog_name="cache-cli",
        cli_kebab_case=True,
        cli_shortcuts={
            "host": "h",
            "repeat": "r",
            "input": "i",
            "json": "j",
            "output": "o",
        },
        cli_avoid_json=True,
    )

    host: Annotated[AnyHttpUrl, Field(description="Base URL of the service")] = AnyHttpUrl(
        "http://localhost:8000"
    )
    repeat: Annotated[int, Field(ge=1, description="Number of iterations")] = 1
    input: Annotated[str | None, Field(description="Input JSON file, '-' for stdin")] = None
    json_input: Annotated[
        str | None, Field(alias="json", description="Input as an inline JSON string")
    ] = None
    output: Annotated[str, Field(description="Output file, '-' for stdout")] = "-"

    @model_validator(mode="after")
    def _exactly_one_input(self) -> Self:
        if (self.input is None) == (self.json_input is None):
            raise ValueError("provide exactly one of --input or --json")
        return self

    def read_request(self) -> PayloadRequest:
        """Load and validate the request body from whichever source was given."""
        if self.json_input is not None:
            raw = self.json_input
        elif self.input == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(self.input).read_text()  # type: ignore[arg-type]
        return PayloadRequest.model_validate_json(raw)


def run(settings: CliSettings, client: httpx.Client | None = None) -> list[dict[str, str]]:
    """POST the payload ``repeat`` times, GET each result, and write them as JSON lines.

    Repeating the identical request is the quick way to check caching: every
    iteration must report the same id.
    """
    request = settings.read_request()
    owns_client = client is None
    client = client or httpx.Client(base_url=str(settings.host), timeout=30)
    results: list[dict[str, str]] = []
    try:
        for _ in range(settings.repeat):
            created = client.post("/payload", json=request.model_dump())
            created.raise_for_status()
            pid = created.json()["id"]
            fetched = client.get(f"/payload/{pid}")
            fetched.raise_for_status()
            results.append({"id": pid, "output": fetched.json()["output"]})
    finally:
        if owns_client:
            client.close()

    lines = "".join(json.dumps(r) + "\n" for r in results)
    if settings.output == "-":
        sys.stdout.write(lines)
    else:
        Path(settings.output).write_text(lines)
    return results


def _parse_args(args: list[str] | None = None) -> CliSettings:
    # pydantic-settings only reserves -h for help on its own parser type, so a
    # plain ArgumentParser lets --host own -h; --help is then registered by hand.
    parser = argparse.ArgumentParser(prog="cache-cli", add_help=False)
    parser.add_argument("--help", action="help", help="show this help message and exit")
    source = CliSettingsSource(CliSettings, root_parser=parser)
    return CliApp.run(CliSettings, cli_args=args, cli_settings_source=source)


def main() -> None:
    try:
        settings = _parse_args()
        run(settings)
    except (ValidationError, OSError, httpx.HTTPError) as exc:
        sys.exit(f"cache-cli: {exc}")
