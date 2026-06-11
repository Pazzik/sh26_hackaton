from app.contracts import PipelineState, ExtractionResult, AnalysisResult
from app.agents.critic import critique

class FakeLLM:
    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, user): return self.payload

def _state():
    st = PipelineState(message="q", deadline_ts=0)
    st.extraction = ExtractionResult(columns=["a"], rows=[{"a": 1}], row_count=1)
    st.analysis = AnalysisResult(findings=["вывод"], numbers={"a": 1.0})
    return st

def test_critique_approve():
    st = critique(_state(), llm=FakeLLM({"approved": True, "issues": [], "must_retry": False}))
    assert st.critique.approved is True
    assert st.trace[-1].agent == "critic"

def test_critique_reject():
    st = critique(_state(), llm=FakeLLM({"approved": False, "issues": ["нет фильтра"], "must_retry": True}))
    assert st.critique.must_retry is True
    assert st.critique.retry_target == "analyst"  # дефолт

def test_critique_retry_target_extractor():
    st = critique(_state(), llm=FakeLLM({"approved": False, "issues": ["не тот срез"],
                                         "must_retry": True, "retry_target": "extractor"}))
    assert st.critique.retry_target == "extractor"

def test_critique_garbage_target_falls_back():
    st = critique(_state(), llm=FakeLLM({"approved": False, "must_retry": True,
                                         "retry_target": "оркестратор"}))
    assert st.critique.retry_target == "analyst"

def test_critique_sees_sql():
    # критик проверяет срез по SQL — он обязан попасть в промпт
    class Spy:
        def complete_json(self, system, user):
            self.last_user = user
            return {"approved": True, "issues": [], "must_retry": False}
    spy = Spy()
    st = _state()
    st.extraction.sql = "SELECT a FROM t WHERE x=1"
    critique(st, llm=spy)
    assert "SELECT a FROM t WHERE x=1" in spy.last_user
