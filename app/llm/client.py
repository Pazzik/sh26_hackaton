import json
import re
from app.config import settings

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

class LLMClient:
    def __init__(self):
        self._client = None  # ленивая инициализация openai

    def _ensure(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=settings.yc_api_key,          # уходит как Authorization: Bearer — Yandex принимает
                base_url=settings.llm_base_url,
                timeout=settings.llm_timeout_sec,
                max_retries=settings.llm_max_retries,
            )
        return self._client

    def _model_uri(self) -> str:
        m = settings.llm_model_uri
        if m.startswith("gpt://") or m.startswith("emb://"):
            return m
        return f"gpt://{settings.yc_folder}/{m}"   # gpt://<folder>/deepseek-v4-flash/latest

    def _raw_complete(self, system: str, user: str) -> str:
        client = self._ensure()
        resp = client.chat.completions.create(
            model=self._model_uri(),
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0,
            max_tokens=settings.llm_max_tokens,       # reasoning-модель: запас под рассуждение
            response_format={"type": "json_object"},
        )
        # финальный ответ в .content; reasoning_content игнорируем
        return resp.choices[0].message.content or ""

    def complete_json(self, system: str, user: str) -> dict:
        try:
            raw = self._raw_complete(system, user)
        except Exception:
            return {}
        text = _FENCE.sub("", raw.strip())
        try:
            val = json.loads(text)
            return val if isinstance(val, dict) else {}
        except Exception:
            return {}

llm = LLMClient()
