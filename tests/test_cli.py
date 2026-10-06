import json

import pytest
from pydantic import ValidationError

from cache_service.cli import CliSettings, _parse_args, run

BODY = {"list_1": ["a", "b"], "list_2": ["c", "d"]}


def test_repeat_returns_same_id_each_time(client, tmp_path):
    out = tmp_path / "out.jsonl"
    settings = _parse_args(["-r", "3", "-j", json.dumps(BODY), "-o", str(out)])

    results = run(settings, client=client)

    assert len(results) == 3
    assert {r["id"] for r in results} == {results[0]["id"]}
    assert results[0]["output"] == "A, C, B, D"
    assert len(out.read_text().splitlines()) == 3


def test_reads_input_file(client, tmp_path, capsys):
    path = tmp_path / "in.json"
    path.write_text(json.dumps(BODY))

    run(_parse_args(["-i", str(path)]), client=client)

    captured = capsys.readouterr()
    print(repr(captured))
    assert json.loads(captured.out)["output"] == "A, C, B, D"


def test_short_flag_h_is_host():
    assert str(_parse_args(["-h", "http://svc:9000", "-j", "{}"]).host) == "http://svc:9000/"


@pytest.mark.parametrize("args", [[], ["-i", "f", "-j", "{}"], ["-r", "0", "-j", "{}"]])
def test_invalid_arguments_rejected(args):
    with pytest.raises((ValidationError, SystemExit)):
        _parse_args(args)


def test_invalid_json_body_rejected():
    with pytest.raises(ValidationError):
        CliSettings(json='{"list_1": ["a"], "list_2": []}').read_request()
