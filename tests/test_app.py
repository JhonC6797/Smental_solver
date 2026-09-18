import numpy as np
import pytest
from fastapi.testclient import TestClient

from semantle.client import GuessResult
from solver.vocabulary import Vocabulary


class InstantClient:
    def get_similarity(self, word):
        return GuessResult(word, 100.0 if word == "בית" else 20.0, None)


@pytest.fixture
def client(monkeypatch, tmp_path):
    words = ["בית", "אוכל", "אדם", "מחשב"]
    rng = np.random.default_rng(7)
    vectors = rng.normal(size=(len(words), 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)

    import server.app as app_module

    monkeypatch.setattr(
        app_module, "load_vocabulary",
        lambda: Vocabulary(words=words, vectors=vectors),
    )
    monkeypatch.setattr(app_module, "SemantleClient", InstantClient)
    monkeypatch.setattr(app_module.config, "PROJECT_ROOT", tmp_path)
    app_module.reset_state()
    return TestClient(app_module.app)


def test_starting_a_run_returns_a_session_id(client):
    response = client.post("/api/solve/start")
    assert response.status_code == 200
    assert response.json()["session_id"]


def test_the_websocket_streams_the_run(client):
    session_id = client.post("/api/solve/start").json()["session_id"]
    received = []
    with client.websocket_connect(f"/ws/solve/{session_id}") as socket:
        while True:
            message = socket.receive_json()
            received.append(message)
            if message["type"] in {"solved", "failed"}:
                break
    assert received[0]["type"] == "run_started"
    assert any(m["type"] == "guess" for m in received)
    assert received[-1]["type"] == "solved"


def test_a_guess_message_carries_a_position(client):
    session_id = client.post("/api/solve/start").json()["session_id"]
    with client.websocket_connect(f"/ws/solve/{session_id}") as socket:
        while True:
            message = socket.receive_json()
            if message["type"] == "guess":
                assert set(message["position"]) == {"x", "y", "z", "radius"}
                return


def test_an_unknown_session_is_rejected(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/solve/nope") as socket:
            socket.receive_json()


def test_the_day_is_solved_once_and_replayed_after(client):
    """Every visitor must not cost the Semantle API another twenty calls."""
    first = client.post("/api/solve/start").json()
    assert first["recorded"] is False
    with client.websocket_connect(f"/ws/solve/{first['session_id']}") as socket:
        while socket.receive_json()["type"] not in {"solved", "failed"}:
            pass

    second = client.post("/api/solve/start").json()
    assert second["recorded"] is True
    assert second["session_id"] == first["session_id"]


def test_health_reports_ready(client):
    assert client.get("/api/health").json() == {"ok": True}
