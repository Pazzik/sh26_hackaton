from app.contracts import PipelineState
from app.agents.extractor import extract

class FakeLLM:
    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, user): return self.payload

def test_extract_runs_sql(data_dir):
    st = PipelineState(message="сколько продуктовых линий", deadline_ts=0)
    st = extract(st, llm=FakeLLM({"sql": "SELECT COUNT(*) n FROM product_lines",
                                  "insufficient": False, "note": None}), data_dir=data_dir)
    assert st.extraction.insufficient is False
    assert st.extraction.row_count == 1
    assert st.trace[-1].agent == "extractor"

def test_extract_insufficient(data_dir):
    st = PipelineState(message="что думают стейкхолдеры", deadline_ts=0)
    st = extract(st, llm=FakeLLM({"sql": "", "insufficient": True, "note": "нет в витрине"}),
                 data_dir=data_dir)
    assert st.extraction.insufficient is True

def test_extract_passes_history(data_dir):
    class Spy:
        def complete_json(self, system, user):
            self.last_user = user
            return {"sql": "SELECT COUNT(*) n FROM product_lines", "insufficient": False, "note": None}
    spy = Spy()
    st = PipelineState(message="а по B-сегменту?", deadline_ts=0,
                       history=[{"role": "user", "content": "выручка по сегментам"}])
    extract(st, llm=spy, data_dir=data_dir)
    assert "выручка по сегментам" in spy.last_user

def test_extract_retries_on_sql_error(data_dir):
    # первый payload — битый SQL, второй — валидный (самокоррекция)
    class TwoStep:
        def __init__(self): self.calls = 0
        def complete_json(self, system, user):
            self.calls += 1
            if self.calls == 1:
                return {"sql": "SELECT bad_col FROM product_lines", "insufficient": False, "note": None}
            return {"sql": "SELECT COUNT(*) n FROM product_lines", "insufficient": False, "note": None}
    st = PipelineState(message="сколько линий", deadline_ts=0)
    st = extract(st, llm=TwoStep(), data_dir=data_dir)
    assert st.extraction.row_count == 1
