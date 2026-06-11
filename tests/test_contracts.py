from app.contracts import (
    RouterDecision, ExtractionResult, AnalysisResult, CritiqueVerdict,
    ChartSpec, TraceStep, PipelineState,
)

def test_pipeline_state_minimal():
    st = PipelineState(message="привет", session_id=None, deadline_ts=123.0)
    assert st.retries_used == 0
    assert st.trace == []
    assert st.route is None

def test_router_decision_kind_validated():
    d = RouterDecision(kind="simple", needs_chart=False, rationale="r")
    assert d.kind == "simple"
    assert RouterDecision(kind="ambiguous").kind == "ambiguous"

def test_critique_retry_target_default():
    v = CritiqueVerdict(approved=False, must_retry=True)
    assert v.retry_target == "analyst"
    assert CritiqueVerdict(retry_target="extractor").retry_target == "extractor"

def test_extraction_defaults():
    e = ExtractionResult(sql="SELECT 1", columns=["a"], rows=[{"a": 1}],
                         row_count=1, truncated=False, insufficient=False, note=None)
    assert e.row_count == 1
