from app.contracts import PipelineState

_TRAP_TEXT = ("В витрине Meridian нет данных, чтобы ответить на этот вопрос однозначно "
              "(например, тексты интервью или мнения стейкхолдеров вне витрины). "
              "Могу ответить на вопросы по выручке, оттоку, NPS, юнит-экономике и марже.")
_CHITCHAT_TEXT = ("Я — аналитик данных Meridian. Задайте вопрос по витрине: выручка, отток, "
                  "NPS, юнит-экономика, маржа по сегментам и продуктовым линиям.")

def build_response(state: PipelineState) -> dict:
    kind = state.route.kind if state.route else "analytical"
    trace = [t.model_dump(exclude_none=True) for t in state.trace]

    if kind == "trap":
        # подмешиваем rationale роутера: отказ объясняет, чего именно нет в витрине,
        # а не выглядит консервированным шаблоном на любой вопрос
        why = state.route.rationale if state.route and state.route.rationale else ""
        text = _TRAP_TEXT + (f" Конкретно: {why}" if why else "")
        return {"response": text, "insufficient_data": True,
                "trace": trace, "session_id": state.session_id}
    if kind == "chitchat":
        return {"response": _CHITCHAT_TEXT, "insufficient_data": False,
                "trace": trace, "session_id": state.session_id}

    ex = state.extraction
    if ex is None or ex.insufficient:
        note = (ex.note if ex and ex.note else "данных недостаточно")
        return {"response": f"Данных недостаточно: {note}.", "insufficient_data": True,
                "trace": trace, "session_id": state.session_id}

    if state.analysis:  # analyst отвечает и на simple (краткий режим), и на analytical
        response = " ".join(state.analysis.findings)
        assumptions = state.analysis.assumptions + state.analysis.caveats
    else:               # fallback: analyst упал/дедлайн — отдаём датасет по-человечески
        response = _summarize_simple(ex)
        assumptions = [ex.note] if ex.note else []

    out = {
        "response": response or "Готово.",
        "assumptions": assumptions,
        "trace": trace,
        "insufficient_data": False,
        "session_id": state.session_id,
    }
    if state.chart and state.chart.type != "none":
        out["chart"] = state.chart.model_dump()
    return out

def _fmt(v) -> str:
    """Человеческий формат значения: без Decimal('...')/datetime.date(...) в ответе."""
    if isinstance(v, float) or str(type(v).__name__) == "Decimal":
        return f"{float(v):,.2f}".replace(",", " ")
    return str(v)

def _summarize_simple(ex) -> str:
    if ex.row_count == 1 and len(ex.columns) == 1:
        col = ex.columns[0]
        return f"{col}: {_fmt(ex.rows[0][col])}."
    lines = ["; ".join(f"{c}={_fmt(r.get(c))}" for c in ex.columns) for r in ex.rows[:5]]
    more = f" Показаны первые 5 из {ex.row_count}." if ex.row_count > 5 else ""
    return (f"По запросу получено строк: {ex.row_count}. " + " | ".join(lines) + "." + more
            + (" Результат усечён лимитом." if ex.truncated else ""))
