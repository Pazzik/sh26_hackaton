from app.contracts import (PipelineState, RouterDecision, ExtractionResult,
                           AnalysisResult, ChartSpec)
from app.agents.answer import build_response

def test_analytical_answer():
    st = PipelineState(message="q", session_id="s1", deadline_ts=0)
    st.route = RouterDecision(kind="analytical")
    st.extraction = ExtractionResult(rows=[{"a": 1}], row_count=1)
    st.analysis = AnalysisResult(findings=["вывод 1", "вывод 2"],
                                 assumptions=["при текущем оттоке"], caveats=["низкая база"])
    st.chart = ChartSpec(type="line", x="m", y="v", reason="r")
    out = build_response(st)
    assert "вывод 1" in out["response"]
    assert "при текущем оттоке" in out["assumptions"]
    assert "низкая база" in out["assumptions"]
    assert out["insufficient_data"] is False
    assert out["session_id"] == "s1"
    assert out["chart"]["type"] == "line"
    assert isinstance(out["trace"], list)

def test_trap_answer():
    st = PipelineState(message="мнение CEO?", deadline_ts=0)
    st.route = RouterDecision(kind="trap", rationale="мнения людей не хранятся в витрине")
    out = build_response(st)
    assert out["insufficient_data"] is True
    assert len(out["response"]) >= 10
    assert "мнения людей" in out["response"]  # отказ объясняет, чего нет, а не шаблонит

def test_insufficient_extraction():
    st = PipelineState(message="q", deadline_ts=0)
    st.route = RouterDecision(kind="analytical")
    st.extraction = ExtractionResult(insufficient=True, note="нет данных")
    out = build_response(st)
    assert out["insufficient_data"] is True
