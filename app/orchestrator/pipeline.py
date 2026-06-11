import time, asyncio, logging
from app.contracts import PipelineState, TraceStep
from app.config import settings
from app.agents import router, extractor, analyst, critic, viz
from app.memory.sessions import store as default_store

log = logging.getLogger("meridian.pipeline")

class _DefaultAgents:
    route = staticmethod(router.route)
    extract = staticmethod(extractor.extract)
    analyze = staticmethod(analyst.analyze)
    critique = staticmethod(critic.critique)
    visualize = staticmethod(viz.visualize)

def _deadline(kind: str) -> float:
    sec = settings.deadline_simple_sec if kind == "simple" else settings.deadline_analytical_sec
    return time.monotonic() + sec

def _expired(state: PipelineState) -> bool:
    return time.monotonic() >= state.deadline_ts

def _guard(state: PipelineState, node: str) -> bool:
    """Дедлайн проверяется перед КАЖДЫМ LLM-узлом: graceful-выход с собранным."""
    if _expired(state):
        state.trace.append(TraceStep(
            agent="orchestrator", summary=f"дедлайн исчерпан перед {node} — отдаём собранное"))
        return False
    return True

def run_pipeline_sync(message: str, session_id: str | None,
                      agents=_DefaultAgents, store=default_store) -> PipelineState:
    state = PipelineState(message=message, session_id=session_id,
                          history=store.get(session_id), deadline_ts=_deadline("analytical"))
    try:
        state = agents.route(state)
        kind = state.route.kind
        state.deadline_ts = _deadline(kind)

        if kind in ("trap", "chitchat"):
            return state

        if not _guard(state, "extractor"):
            return state
        state = agents.extract(state)
        if state.extraction.insufficient:
            return state

        if kind == "simple":
            # analyst в кратком режиме: ответ на языке бизнеса, без сырого дампа строк
            if _guard(state, "analyst"):
                state = agents.analyze(state, brief=True)
            state = agents.visualize(state)
            return state

        # analytical | ambiguous (толкование вопроса analyst кладёт в assumptions)
        if not _guard(state, "analyst"):
            return state
        state = agents.analyze(state)
        if not _guard(state, "critic"):
            return state
        state = agents.critique(state)
        if (state.critique.must_retry and state.retries_used < settings.critic_max_retries
                and not _expired(state)):
            state.retries_used += 1
            if state.critique.retry_target == "extractor":  # неверен сам срез
                state = agents.extract(state, feedback=state.critique.issues)
            state = agents.analyze(state, feedback=state.critique.issues)
            if _guard(state, "critic"):
                state = agents.critique(state)
        state = agents.visualize(state)
        return state
    except Exception as e:
        log.exception("сбой пайплайна")  # деградируем честно, но стектрейс сохраняем себе
        state.trace.append(TraceStep(agent="error", summary=f"сбой пайплайна: {e}"[:200]))
        return state

async def run_pipeline(message: str, session_id: str | None, agents=_DefaultAgents,
                       store=default_store) -> PipelineState:
    return await asyncio.to_thread(run_pipeline_sync, message, session_id, agents, store)
