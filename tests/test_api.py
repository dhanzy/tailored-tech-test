SAMPLE = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}


def test_create_then_read_matches_sample(client):
    created = client.post("/payload", json=SAMPLE)
    assert created.status_code == 201

    fetched = client.get(f"/payload/{created.json()['id']}")
    assert fetched.json() == {
        "output": "FIRST STRING, OTHER STRING, SECOND STRING, "
        "ANOTHER STRING, THIRD STRING, LAST STRING"
    }


def test_identical_request_reuses_id_without_calling_transformer(client, transformer):
    first = client.post("/payload", json=SAMPLE).json()["id"]
    calls_after_first = len(transformer.calls)

    assert client.post("/payload", json=SAMPLE).json()["id"] == first
    assert len(transformer.calls) == calls_after_first


def test_shared_strings_are_transformed_once(client, transformer):
    client.post("/payload", json={"list_1": ["a", "b"], "list_2": ["a", "c"]})
    client.post("/payload", json={"list_1": ["b", "c"], "list_2": ["d", "a"]})

    # Only unique strings ever reach the transformer: a, b, c, then d.
    assert sorted(transformer.calls) == ["a", "b", "c", "d"]


def test_swapped_lists_are_a_different_payload(client):
    a = client.post("/payload", json={"list_1": ["x"], "list_2": ["y"]}).json()["id"]
    b = client.post("/payload", json={"list_1": ["y"], "list_2": ["x"]}).json()["id"]
    assert a != b
    assert client.get(f"/payload/{b}").json() == {"output": "Y, X"}


def test_unequal_lengths_rejected(client):
    response = client.post("/payload", json={"list_1": ["a"], "list_2": []})
    assert response.status_code == 422


def test_unknown_id_is_404(client):
    assert client.get("/payload/nope").status_code == 404


def test_empty_lists_produce_empty_output(client):
    pid = client.post("/payload", json={"list_1": [], "list_2": []}).json()["id"]
    assert client.get(f"/payload/{pid}").json() == {"output": ""}


def test_cache_hits_and_misses_are_logged(client, caplog):
    caplog.set_level("INFO", logger="cache_service.service")
    body = {"list_1": ["a", "b"], "list_2": ["a", "c"]}

    client.post("/payload", json=body)
    assert "payload cache miss" in caplog.text
    assert "string cache: 0 hits, 3 misses" in caplog.text

    caplog.clear()
    client.post("/payload", json=body)
    assert "payload cache hit" in caplog.text
