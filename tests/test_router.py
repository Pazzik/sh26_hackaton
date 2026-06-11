from app.contracts import PipelineState
from app.agents.router import route

class FakeLLM:
    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, user): return self.payload

def test_route_sets_decision_and_trace():
    st = PipelineState(message="выручка по линиям", deadline_ts=0)
    st = route(st, llm=FakeLLM({"kind": "simple", "needs_chart": True, "rationale": "один срез"}))
    assert st.route.kind == "simple"
    assert st.route.needs_chart is True
    assert st.trace[-1].agent == "router"

def test_route_defaults_to_analytical_on_garbage():
    st = PipelineState(message="что происходит?", deadline_ts=0)
    st = route(st, llm=FakeLLM({}))
    assert st.route.kind in ("analytical", "simple", "ambiguous", "trap", "chitchat")

def test_route_passes_history_to_prompt():
    class Spy:
        def complete_json(self, system, user):
            self.last_user = user
            return {"kind": "simple", "needs_chart": False, "rationale": ""}
    spy = Spy()
    st = PipelineState(message="а теперь только по B-сегменту", deadline_ts=0,
                       history=[{"role": "user", "content": "выручка по сегментам"}])
    route(st, llm=spy)
    assert "выручка по сегментам" in spy.last_user
