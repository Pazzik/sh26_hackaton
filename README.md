# Meridian AI Analyst

Мультиагентный AI-аналитик данных Meridian (AI South Hack).

## Запуск

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export YC_API_KEY=...                       # ключ Yandex AI Studio (см. access.local.md)
export YC_FOLDER_ID=b1gm5lt4p9630hifld2j    # каталог команды (fallback: YC_FOLDER)
export LLM_MODEL_URI=deepseek-v4-flash/latest   # точный ID DeepSeek v4 (проверен)
# строго ОДИН worker: сессии и DuckDB живут в памяти процесса,
# несколько воркеров развалят диалоговый контекст
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Проверка

```bash
curl -s localhost:8000/health
curl -s localhost:8000/api/chat -H 'content-type: application/json' \
  -d '{"message":"Покажи выручку по продуктовым линиям"}'
```

## Тесты

```bash
pytest -q                 # оффлайн (LLM мокается)
pytest -m live -v -s      # сценарные с реальной LLM (нужен YC_API_KEY)
```

## Архитектура

См. `docs/superpowers/specs/2026-06-11-multiagent-analyst-design.md`.
Поток: router → (simple: extractor→analyst-кратко→viz) /
(analytical/ambiguous: extractor→analyst→critic≤1 [retry_target]→viz) → answer.
