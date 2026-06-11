import json
from app.llm.client import LLMClient

class FakeClient(LLMClient):
    def __init__(self, payload):
        self._payload = payload
    def _raw_complete(self, system, user):
        return self._payload

def test_complete_json_parses_object():
    c = FakeClient(json.dumps({"kind": "simple", "needs_chart": False}))
    out = c.complete_json("sys", "usr")
    assert out["kind"] == "simple"

def test_complete_json_strips_codefence():
    c = FakeClient("```json\n{\"a\": 1}\n```")
    assert c.complete_json("s", "u") == {"a": 1}

def test_complete_json_returns_empty_on_garbage():
    c = FakeClient("это не json")
    assert c.complete_json("s", "u") == {}
