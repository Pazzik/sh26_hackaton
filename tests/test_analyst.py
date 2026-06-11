from app.contracts import PipelineState, ExtractionResult
from app.agents.analyst import analyze

class FakeLLM:
    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, user):
        self.last_user = user
        return self.payload

def test_analyze_fills_result():
    st = PipelineState(message="динамика выручки", deadline_ts=0)
    st.extraction = ExtractionResult(columns=["year", "rev"], rows=[{"year": 2024, "rev": 10}],
                                     row_count=1, insufficient=False)
    st = analyze(st, llm=FakeLLM({"findings": ["выручка упала на 15%"],
                                  "numbers": {"drop_pct": -15.0}, "assumptions": [],
                                  "caveats": ["низкая база"]}))
    assert st.analysis.findings
    assert st.analysis.numbers["drop_pct"] == -15.0
    assert st.trace[-1].agent == "analyst"

def test_analyze_passes_feedback():
    st = PipelineState(message="q", deadline_ts=0)
    st.extraction = ExtractionResult(columns=["a"], rows=[{"a": 1}], row_count=1)
    llm = FakeLLM({"findings": ["x"], "numbers": {}, "assumptions": [], "caveats": []})
    st = analyze(st, llm=llm, feedback=["проверь фильтр по сегменту"])
    assert "проверь фильтр" in llm.last_user

def test_analyze_brief_mode_in_prompt():
    st = PipelineState(message="выручка по линиям", deadline_ts=0)
    st.extraction = ExtractionResult(columns=["a"], rows=[{"a": 1}], row_count=1)
    llm = FakeLLM({"findings": ["x"], "numbers": {}, "assumptions": [], "caveats": []})
    analyze(st, llm=llm, brief=True)
    assert "brief" in llm.last_user.lower()

def test_analyze_truncation_is_honest():
    # аналитик видит максимум 200 строк — если их больше, он обязан об этом знать
    st = PipelineState(message="q", deadline_ts=0)
    rows = [{"a": i} for i in range(500)]
    st.extraction = ExtractionResult(columns=["a"], rows=rows, row_count=500, truncated=False)
    llm = FakeLLM({"findings": ["x"], "numbers": {}, "assumptions": [], "caveats": []})
    analyze(st, llm=llm)
    assert '"truncated": true' in llm.last_user
    assert '"total_rows": 500' in llm.last_user
