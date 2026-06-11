import os
from dataclasses import dataclass

# ⚠️ Футган dataclass: дефолты полей вычисляются ОДИН РАЗ при импорте модуля —
# смена env после импорта ни на что не влияет. Это осознанно (12-factor: env
# выставляется до старта процесса); в тестах перезаписывать поля экземпляра.

@dataclass
class Settings:
    yc_api_key: str = os.getenv("YC_API_KEY", "")
    # каталог Yandex Cloud: канон — YC_FOLDER_ID (конвенция yc CLI / окружения VM);
    # YC_FOLDER оставлен fallback'ом для уже выставленных окружений
    yc_folder: str = os.getenv("YC_FOLDER_ID") or os.getenv("YC_FOLDER", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://ai.api.cloud.yandex.net/v1")
    # DeepSeek v4 в каталоге AI Studio — точный ID проверен на ключе команды 2026-06-11.
    # Хранится короткий ID; полный URI gpt://<folder>/<id> собирает LLMClient.
    llm_model_uri: str = os.getenv("LLM_MODEL_URI", "deepseek-v4-flash/latest")
    # 60s × (1+1 retry) = худший LLM-вызов ≤ 120 c; худший путь ~8 вызовов
    # укладывается в потолок контракта 10 мин (см. гарантии дедлайна в спеке)
    llm_timeout_sec: float = float(os.getenv("LLM_TIMEOUT_SEC", "60"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "1"))
    # reasoning-модель тратит токены на рассуждение до финального ответа — запас
    # обязателен; у analyst самый длинный вывод (findings+numbers+caveats)
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "3000"))
    deadline_simple_sec: int = int(os.getenv("DEADLINE_SIMPLE_SEC", "300"))
    deadline_analytical_sec: int = int(os.getenv("DEADLINE_ANALYTICAL_SEC", "600"))
    sql_row_limit: int = int(os.getenv("SQL_ROW_LIMIT", "5000"))
    max_chart_points: int = int(os.getenv("MAX_CHART_POINTS", "200"))
    sql_timeout_sec: float = float(os.getenv("SQL_TIMEOUT_SEC", "20"))
    critic_max_retries: int = int(os.getenv("CRITIC_MAX_RETRIES", "1"))
    session_ttl_sec: int = int(os.getenv("SESSION_TTL_SEC", "1800"))
    max_question_chars: int = int(os.getenv("MAX_QUESTION_CHARS", "8000"))

settings = Settings()
