import pytest, httpx
from httpx import ASGITransport
from app.api.main import app
from app.contracts import PipelineState, RouterDecision

@pytest.fixture
def client(monkeypatch):
    # подменяем пайплайн, чтобы не ходить в LLM/данные
    async def fake_pipeline(message, session_id, **k):
        st = PipelineState(message=message, session_id=session_id, deadline_ts=0)
        st.route = RouterDecision(kind="chitchat")
        return st
    monkeypatch.setattr("app.api.main.run_pipeline", fake_pipeline)
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

async def test_docs_and_openapi_alive(client):
    # бонусные баллы контракта: /docs и /openapi.json
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200

@pytest.mark.parametrize("path", ["/api/chat", "/api/v1/chat", "/chat", "/api/ask", "/api/query"])
async def test_all_paths_answer(client, path):
    r = await client.post(path, json={"message": "привет"})
    assert r.status_code == 200
    assert len(r.json()["response"]) >= 10

async def test_empty_body_400_not_500(client):
    r = await client.post("/api/chat", json={})
    assert r.status_code == 400

async def test_invalid_json_not_500(client):
    r = await client.post("/api/chat", content=b"{not json",
                          headers={"content-type": "application/json"})
    assert r.status_code in (400, 422)

async def test_non_string_422(client):
    r = await client.post("/api/chat", json={"message": 123})
    assert r.status_code == 422

async def test_unknown_path_404(client):
    r = await client.post("/api/nonexistent", json={"message": "x"})
    assert r.status_code == 404

async def test_garbage_session_id_not_500(client):
    # dict вместо session_id не должен ронять диалоговый слой (белый хакинг);
    # prompt-injection здесь не тестируем: с замоканным пайплайном кейс тривиален,
    # он живёт в test_live_scenarios.py с реальной LLM
    r = await client.post("/api/chat", json={"message": "привет", "session_id": {"a": 1}})
    assert r.status_code == 200
    assert len(r.json()["response"]) >= 10
