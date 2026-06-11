import time
from datetime import date, datetime
from decimal import Decimal
from app.config import settings
from app.contracts import PipelineState, ChartSpec, TraceStep

_TIME_HINTS = ("month", "quarter", "year", "date", "day")

def _looks_temporal(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in _TIME_HINTS)

def _json_safe(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v

def _chart_data(rows: list[dict]) -> list[dict]:
    return [{k: _json_safe(val) for k, val in r.items()}
            for r in rows[: settings.max_chart_points]]

def visualize(state: PipelineState) -> PipelineState:
    t0 = time.monotonic()
    ex = state.extraction
    cols, rows = (ex.columns, ex.rows) if ex else ([], [])

    if not rows or len(rows) == 1:
        # одно число ИЛИ одна строка: график из единственной точки бессмыслен
        spec = ChartSpec(type="none", reason="одна строка/одно число — график не нужен")
    elif len(cols) >= 2 and _looks_temporal(cols[0]):
        spec = ChartSpec(type="line", x=cols[0], y=cols[1],
                         series=cols[2] if len(cols) > 2 else None,
                         reason="динамика во времени")
    elif len(cols) >= 2:
        spec = ChartSpec(type="bar", x=cols[0], y=cols[1],
                         reason="сравнение по категориям")
    else:
        spec = ChartSpec(type="none", reason="график не уместен")

    if spec.type != "none":
        spec.data = _chart_data(rows)

    state.chart = spec
    state.trace.append(TraceStep(agent="viz", summary=f"{spec.type}: {spec.reason}",
                                 elapsed_ms=int((time.monotonic() - t0) * 1000)))
    return state
