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

import json
from datetime import date
from decimal import Decimal

def test_bar_data_equals_rows():
    rows = [{"line": "A", "rev": 1}, {"line": "B", "rev": 2}]
    st = visualize(_st(["line", "rev"], rows))
    assert st.chart.type == "bar"
    assert st.chart.data == rows

def test_none_chart_has_empty_data():
    st = visualize(_st(["n"], [{"n": 42}]))
    assert st.chart.type == "none"
    assert st.chart.data == []

def test_data_truncated_to_limit(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_chart_points", 3)
    rows = [{"month": f"2024-{i:02d}", "rev": i} for i in range(1, 13)]
    st = visualize(_st(["month", "rev"], rows))
    assert len(st.chart.data) == 3

def test_data_is_json_safe():
    # DuckDB отдаёт Decimal/date — они должны стать сериализуемыми
    rows = [{"d": date(2024, 1, 1), "rev": Decimal("1.5")},
            {"d": date(2024, 2, 1), "rev": Decimal("2.5")}]
    st = visualize(_st(["d", "rev"], rows))
    json.dumps(st.chart.data)  # не должно бросить TypeError
    assert st.chart.data[0]["rev"] == 1.5
    assert st.chart.data[0]["d"] == "2024-01-01"
