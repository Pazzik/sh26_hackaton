from app.contracts import PipelineState, ExtractionResult
from app.agents.viz import visualize

def _st(columns, rows):
    st = PipelineState(message="q", deadline_ts=0)
    st.extraction = ExtractionResult(columns=columns, rows=rows, row_count=len(rows))
    return st

def test_single_number_no_chart():
    st = visualize(_st(["n"], [{"n": 42}]))
    assert st.chart.type == "none"

def test_single_row_many_cols_no_chart():
    # line/bar из единственной точки бессмыслен, даже если первая колонка временнАя
    st = visualize(_st(["year", "rev", "ebitda"], [{"year": 2025, "rev": 1, "ebitda": -2}]))
    assert st.chart.type == "none"

def test_timeseries_is_line():
    rows = [{"month": "2024-01", "rev": 1}, {"month": "2024-02", "rev": 2}]
    st = visualize(_st(["month", "rev"], rows))
    assert st.chart.type == "line"
    assert st.chart.x == "month"

def test_category_compare_is_bar():
    rows = [{"line": "A", "rev": 1}, {"line": "B", "rev": 2}]
    st = visualize(_st(["line", "rev"], rows))
    assert st.chart.type == "bar"

def test_chartspec_has_data_default_empty():
    from app.contracts import ChartSpec
    assert ChartSpec().data == []

def test_config_has_max_chart_points():
    from app.config import settings
    assert isinstance(settings.max_chart_points, int)
    assert settings.max_chart_points > 0
