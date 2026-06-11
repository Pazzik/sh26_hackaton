import time
from app.contracts import PipelineState, RouterDecision, TraceStep
from app.agents.prompts import ROUTER
from app.llm.client import llm as default_llm

def format_history(history: list[dict], max_turns: int = 6) -> str:
    """Последние реплики сессии для промпта (общий хелпер router/extractor)."""
    if not history:
        return ""
    lines = [f"{m.get('role', '?')}: {m.get('content', '')}" for m in history[-max_turns:]]
    return "<history>\n" + "\n".join(lines) + "\n</history>\n\n"

def route(state: PipelineState, llm=default_llm) -> PipelineState:
    t0 = time.monotonic()
    user = format_history(state.history) + f"<question>\n{state.message}\n</question>"
    data = llm.complete_json(ROUTER, user)
    kind = data.get("kind")
    if kind not in ("simple", "analytical", "ambiguous", "trap", "chitchat"):
        kind = "analytical"  # безопасный дефолт: полный путь с критиком
    state.route = RouterDecision(
        kind=kind,
        needs_chart=bool(data.get("needs_chart", False)),
        rationale=str(data.get("rationale", "")),
    )
    state.trace.append(TraceStep(
        agent="router", summary=f"kind={kind}: {state.route.rationale}"[:200],
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    ))
    return state
