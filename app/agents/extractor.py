import time
from app.contracts import PipelineState, ExtractionResult, TraceStep
from app.agents.prompts import EXTRACTOR
from app.agents.router import format_history
from app.data.schema_card import SCHEMA_CARD
from app.data.executor import run_query
from app.llm.client import llm as default_llm

def _ask(llm, state, error_hint="", feedback=None):
    system = EXTRACTOR.replace("{schema_card}", SCHEMA_CARD)
    user = format_history(state.history) + f"<question>\n{state.message}\n</question>"
    if feedback:  # критик вернул на доработку среза
        user += "\n\nКритик счёл срез неверным, учти замечания:\n- " + "\n- ".join(feedback)
        if state.extraction and state.extraction.sql:
            user += f"\n\nПредыдущий SQL:\n{state.extraction.sql}"
    if error_hint:
        user += f"\n\nПредыдущий SQL дал ошибку, исправь:\n{error_hint}"
    return llm.complete_json(system, user)

def extract(state: PipelineState, llm=default_llm, data_dir=None,
            feedback: list[str] | None = None) -> PipelineState:
    t0 = time.monotonic()
    data = _ask(llm, state, feedback=feedback)
    if data.get("insufficient"):
        state.extraction = ExtractionResult(insufficient=True, note=data.get("note"))
        state.trace.append(TraceStep(agent="extractor", summary="данных в витрине нет",
                                     elapsed_ms=int((time.monotonic() - t0) * 1000)))
        return state

    sql = str(data.get("sql", "")).strip()
    res = run_query(sql, data_dir=data_dir)
    if res.error:  # одна попытка самокоррекции
        data = _ask(llm, state, error_hint=res.error, feedback=feedback)
        sql = str(data.get("sql", "")).strip()
        res = run_query(sql, data_dir=data_dir)

    if res.error or not sql:
        state.extraction = ExtractionResult(sql=sql, insufficient=True,
                                            note=f"не удалось извлечь данные: {res.error}")
    else:
        state.extraction = ExtractionResult(
            sql=res.sql, columns=res.columns, rows=res.rows, row_count=res.row_count,
            truncated=res.truncated, insufficient=False, note=data.get("note"),
        )
    state.trace.append(TraceStep(
        agent="extractor", summary=f"rows={state.extraction.row_count} truncated={state.extraction.truncated}",
        sql=sql or None, rows=state.extraction.row_count,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    ))
    return state
