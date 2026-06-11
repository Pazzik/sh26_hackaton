import time
from types import SimpleNamespace
from app.contracts import (PipelineState, RouterDecision, ExtractionResult,
                           AnalysisResult, CritiqueVerdict)
from app.orchestrator.pipeline import run_pipeline_sync

def make_agents(kind="analytical", critic_retry=False, retry_target="analyst"):
    calls = {"extract": 0, "analyst": 0, "critic": 0, "brief": None}
    def route(st, **k): st.route = RouterDecision(kind=kind); return st
    def extract(st, **k):
        calls["extract"] += 1
        st.extraction = ExtractionResult(columns=["a"], rows=[{"a": 1}], row_count=1); return st
    def analyze(st, **k):
        calls["analyst"] += 1; calls["brief"] = k.get("brief", False)
        st.analysis = AnalysisResult(findings=["f"]); return st
    def critic(st, **k):
        calls["critic"] += 1
        retry = critic_retry and calls["critic"] == 1
        st.critique = CritiqueVerdict(approved=not retry, must_retry=retry,
                                      retry_target=retry_target); return st
    def visualize(st, **k): return st
    ag = SimpleNamespace(route=route, extract=extract, analyze=analyze,
                         critique=critic, visualize=visualize)
    return ag, calls

def test_simple_path_brief_analyst_no_critic():
    # simple идёт через analyst (краткий режим) — иначе ответ был бы дампом строк,
    # а LLM-судья оценивает интерпретацию; критик на simple не зовётся
    ag, calls = make_agents(kind="simple")
    st = run_pipeline_sync("q", None, agents=ag)
    assert calls["analyst"] == 1 and calls["brief"] is True
    assert calls["critic"] == 0
    assert st.extraction.row_count == 1

def test_analytical_critic_retry_limited_to_one():
    ag, calls = make_agents(kind="analytical", critic_retry=True)
    st = run_pipeline_sync("q", None, agents=ag)
    assert calls["analyst"] == 2   # исходный + 1 доработка
    assert calls["critic"] == 2
    assert st.retries_used == 1

def test_retry_target_extractor_reruns_extraction():
    # неверный срез лечится повтором extractor, а не analyst на том же датасете
    ag, calls = make_agents(kind="analytical", critic_retry=True, retry_target="extractor")
    run_pipeline_sync("q", None, agents=ag)
    assert calls["extract"] == 2
    assert calls["analyst"] == 2

def test_ambiguous_goes_full_path():
    ag, calls = make_agents(kind="ambiguous")
    run_pipeline_sync("q", None, agents=ag)
    assert calls["analyst"] == 1 and calls["critic"] == 1

def test_trap_skips_data_agents():
    ag, calls = make_agents(kind="trap")
    st = run_pipeline_sync("q", None, agents=ag)
    assert calls["analyst"] == 0
    assert st.extraction is None

def test_deadline_graceful_exit():
    # дедлайн истёк после extract → analyst/critic не зовутся, ответ собирается из имеющегося
    ag, calls = make_agents(kind="analytical")
    real_extract = ag.extract
    def slow_extract(st, **k):
        st = real_extract(st, **k)
        st.deadline_ts = 0.0   # симулируем исчерпание бюджета (monotonic > 0)
        return st
    ag.extract = slow_extract
    st = run_pipeline_sync("q", None, agents=ag)
    assert calls["analyst"] == 0
    assert any("дедлайн" in t.summary for t in st.trace)

def test_node_exception_does_not_crash():
    ag, _ = make_agents(kind="analytical")
    def boom(st, **k): raise RuntimeError("boom")
    ag.analyze = boom
    st = run_pipeline_sync("q", None, agents=ag)  # не должно бросить
    assert any(t.agent == "error" for t in st.trace)
