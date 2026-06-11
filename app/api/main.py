import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.parsing import extract_question, BadRequest
from app.api.errors import error_payload
from app.orchestrator.pipeline import run_pipeline
from app.agents.answer import build_response
from app.memory.sessions import store

log = logging.getLogger("meridian.api")

app = FastAPI(title="Meridian AI Analyst", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CHAT_PATHS = ["/api/chat", "/api/v1/chat", "/chat", "/api/ask", "/api/query"]

async def _handle_chat(request: Request) -> JSONResponse:
    # 1) разбор тела — любые ошибки парсинга → 400/422, не 500
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error_payload("невалидный JSON"))
    try:
        question = extract_question(body)
    except BadRequest as e:
        return JSONResponse(status_code=e.status, content=error_payload(e.message))

    # dict/list вместо session_id не должны ломать store (нехешируемый ключ → TypeError)
    raw_sid = body.get("session_id") if isinstance(body, dict) else None
    session_id = str(raw_sid) if isinstance(raw_sid, (str, int)) and str(raw_sid).strip() else None

    # 2) пайплайн — любой сбой ядра → 200 с честным текстом, никогда 500
    try:
        # порядок важен: пайплайн читает историю из store сам (store.get) —
        # текущий вопрос дописываем ПОСЛЕ, иначе он задублируется в своём же контексте
        state = await run_pipeline(question, session_id)
        out = build_response(state)
        store.append(session_id, "user", question)
        store.append(session_id, "assistant", out.get("response", ""))
        return JSONResponse(status_code=200, content=out)
    except Exception:
        # наружу — никогда 500, но себе — полный стектрейс: на белом хакинге
        # без логов не понять, чем именно нас уронили
        log.exception("сбой ядра при обработке запроса")
        return JSONResponse(status_code=200, content={
            "response": "Не удалось обработать запрос из-за внутренней ошибки. "
                        "Попробуйте переформулировать вопрос.",
            "insufficient_data": True,
        })

for _p in CHAT_PATHS:
    app.add_api_route(_p, _handle_chat, methods=["POST"])

@app.get("/health")
async def health():
    return {"status": "ok"}
