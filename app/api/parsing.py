from app.config import settings

class BadRequest(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)

def extract_question(body) -> str:
    if not isinstance(body, dict) or not body:
        raise BadRequest(400, "пустое или некорректное тело запроса")

    raw = None
    if "message" in body:
        raw = body["message"]
    elif "query" in body:
        raw = body["query"]
    elif "messages" in body:
        msgs = body["messages"]
        if not isinstance(msgs, list) or not msgs:
            raise BadRequest(422, "messages должен быть непустым списком")
        users = [m for m in msgs if isinstance(m, dict) and m.get("role") == "user"]
        last = (users or msgs)[-1]
        raw = last.get("content") if isinstance(last, dict) else None
    else:
        raise BadRequest(422, "нет поля с вопросом (message/query/messages)")

    if not isinstance(raw, str):
        raise BadRequest(422, "поле с вопросом должно быть строкой")
    if not raw.strip():
        raise BadRequest(400, "пустой вопрос")
    return raw[: settings.max_question_chars]
