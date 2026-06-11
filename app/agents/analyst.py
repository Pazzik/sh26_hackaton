import time, json
from app.contracts import PipelineState, AnalysisResult, TraceStep
from app.agents.prompts import ANALYST
from app.llm.client import llm as default_llm

def analyze(state: PipelineState, llm=default_llm, feedback: list[str] | None = None,
            brief: bool = False) -> PipelineState:
    t0 = time.monotonic()
    ex = state.extraction
    shown = ex.rows[:200]
    # truncated честный: аналитик видит максимум 200 строк, даже если executor отдал больше —
    # иначе он считает, что видит всё, и делает вывод по куску данных
    dataset = {"columns": ex.columns, "rows": shown, "total_rows": ex.row_count,
               "truncated": ex.truncated or ex.row_count > len(shown), "note": ex.note}
    user = (f"<question>\n{state.message}\n</question>\n\n"
            f"Датасет (JSON):\n{json.dumps(dataset, ensure_ascii=False, default=str)}")
    if brief:  # simple-путь: ответ на языке бизнеса, но без развёрнутого анализа
        user += "\n\nРежим brief: 1–2 ёмких предложения с конкретными числами."
    if feedback:
        user += "\n\nКритик вернул на доработку, устрани:\n- " + "\n- ".join(feedback)
    data = llm.complete_json(ANALYST, user)
    state.analysis = AnalysisResult(
        findings=[str(x) for x in data.get("findings", [])] or ["Не удалось сформулировать вывод."],
        numbers={k: float(v) for k, v in data.get("numbers", {}).items()
                 if isinstance(v, (int, float))},
        assumptions=[str(x) for x in data.get("assumptions", [])],
        caveats=[str(x) for x in data.get("caveats", [])],
    )
    state.trace.append(TraceStep(
        agent="analyst", summary=f"findings={len(state.analysis.findings)}",
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    ))
    return state
