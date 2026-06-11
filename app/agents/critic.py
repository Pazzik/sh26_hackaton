import time, json
from app.contracts import PipelineState, CritiqueVerdict, TraceStep
from app.agents.prompts import CRITIC
from app.llm.client import llm as default_llm

def critique(state: PipelineState, llm=default_llm) -> PipelineState:
    t0 = time.monotonic()
    payload = {
        "question": state.message,
        # SQL обязателен: по одним строкам результата потерянный фильтр/период не увидеть,
        # а решение retry_target=extractor критик принимает именно по срезу
        "sql": state.extraction.sql,
        "dataset": {"columns": state.extraction.columns, "rows": state.extraction.rows[:200],
                    "note": state.extraction.note},
        "analysis": state.analysis.model_dump(),
    }
    user = json.dumps(payload, ensure_ascii=False, default=str)
    data = llm.complete_json(CRITIC, user)
    approved = bool(data.get("approved", True))
    target = data.get("retry_target")
    state.critique = CritiqueVerdict(
        approved=approved,
        issues=[str(x) for x in data.get("issues", [])],
        must_retry=bool(data.get("must_retry", not approved)),
        retry_target=target if target in ("analyst", "extractor") else "analyst",
    )
    state.trace.append(TraceStep(
        agent="critic", verdict="approved" if approved else "needs_revision",
        summary="; ".join(state.critique.issues)[:200] or "ок",
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    ))
    return state
