# Yandex AI Studio — Conversations API (управление контекстом диалога)

> Источник: https://aistudio.yandex.ru/docs/ru/ai-studio/concepts/agents/conversations-api.html
> Раздел: AI Studio → Агенты → Управление контекстом текстового диалога.
> Скачано вручную (домен за антиботом/капчей, прямой `curl`/`WebFetch` недоступны из контура).

## Управление контекстом текстового диалога

При работе с **Responses API** для управления контекстом есть три способа:

1. соединять ответы друг с другом (`previous_response_id`);
2. передавать историю сообщений в каждом запросе;
3. использовать **Conversations API** — хранить диалог как **долгоживущий объект со стабильным идентификатором**.

## Что хранит Conversations API

Conversations API воссоздаёт состояние диалога с помощью сохранённых элементов:

- сообщения пользователя и ассистента;
- вызовы инструментов (tool calls);
- другие служебные сообщения.

> **Ограничения:** редактирование элементов и обнуление диалога сейчас **не поддерживаются**.
> Чтобы перезагрузить диалог, создайте новый объект `conversation`.

## Пример (Python, OpenAI-совместимый клиент)

В многошаговом диалоге объект `conversation` передаётся в следующие запросы, чтобы сохранять
состояние и разделять контекст между ответами:

```python
import openai

YANDEX_CLOUD_FOLDER = "<идентификатор_каталога>"
YANDEX_CLOUD_API_KEY = "<API-ключ>"
YANDEX_CLOUD_MODEL = "yandexgpt"

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)

# Создаём conversation
conv = client.conversations.create()

# Первое сообщение с системной инструкцией и пользовательским вводом
r1 = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    conversation=conv.id,
    input=[
        {"role": "system", "content": "Ты мой ассистент"},
        {"role": "user", "content": "Привет! Запомни: меня зовут Настя."}
    ]
)
print("assistant:", r1.output_text)

# Продолжаем в том же conversation
r2 = client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    conversation=conv.id,
    input="Как меня зовут?"
)
print("assistant:", r2.output_text)
```

## Связанное (для нашего проекта)

- AI Studio API **OpenAI-совместим**: `base_url="https://ai.api.cloud.yandex.net/v1"`,
  модель задаётся как `gpt://<folder>/<model>`.
- Старый **AI Assistant API** (threads) выводится из строя: не поддерживается с 10 декабря 2025,
  полностью отключается 26 января 2026 → диалоговый контекст строим на **Responses + Conversations API**.
- Маппинг на наш API-контракт: `session_id` из `POST /api/chat` ↔ `conversation.id` (стабильный ID
  диалога на стороне AI Studio). Новая сессия → новый `client.conversations.create()`.

## ✅ Подтверждено на нашем ключе команды (2026-06-11)

Реальные вызовы с ключом из `access.local.md` (folder `b1gm5lt4p9630hifld2j`):

- **Авторизация:** работают оба заголовка — `Authorization: Api-Key <key>` (curl) и
  `Authorization: Bearer <key>` (как шлёт `openai` SDK через `api_key=`). HTTP 200.
- **Base URL:** `https://ai.api.cloud.yandex.net/v1` отвечает (корень даёт 404 — это норма).
  Доку Yandex также упоминает `https://llm.api.cloud.yandex.net/v1` — оба ведут себя одинаково.
- **Модель DeepSeek v4 — точный ID: `deepseek-v4-flash/latest`** (не `deepseek-v4`!).
  Полный URI: `gpt://b1gm5lt4p9630hifld2j/deepseek-v4-flash/latest`.
- **DeepSeek v4 — это reasoning-модель:**
  - Рассуждение приходит в `choices[0].message.reasoning_content`, **финальный ответ — в
    `choices[0].message.content`**. При малом `max_tokens` (напр. 20) ответ обрезается на
    середине reasoning и `content=null`, `finish_reason="length"`.
  - **Вывод: ставить `max_tokens` с запасом (≥ 1500–2000)** — reasoning тратит токены до
    финального ответа. Для коротких структурных ответов (роутер) ~200 completion-токенов уходит
    на reasoning; это надо закладывать в бюджет «Экономики».
  - `response_format={"type":"json_object"}` **работает**: `content` приходит валидным JSON,
    reasoning отделён. JSON-режим на нашем LLM-клиенте применим.
  - Латентность простого вызова ~3.4–3.7 s.
- **Responses API** (`client.responses.create`, поля `instructions`/`input`/`max_output_tokens`)
  тоже работает; reasoning лежит в `output[].summary`. Для наших per-agent промптов используем
  **chat/completions** (проще и единообразнее), Conversations API не задействуем.

### Что доступно в нашем каталоге (проверено перебором)

- ✅ `deepseek-v4-flash/latest` — целевая модель (analyst/critic/extractor).
- ✅ `qwen3-235b-a22b-fp8/latest`, `gpt-oss-120b/latest`, `gpt-oss-20b/latest` — запасные сильные.
- ✅ `yandexgpt/latest`, `yandexgpt-32k/latest`, `yandexgpt-lite/latest` (lite — дёшево для роутера).
- ❌ `deepseek-v4`/`deepseek-v3`/`deepseek-r1` без суффикса `-flash`, `llama*`, `gemma*`,
  `qwen3-8b` — «Failed to get model» / forbidden. `GET /v1/models` отдаёт 403 (норма).

### Минимальный рабочий curl (для смоук-теста)

```bash
KEY=...; FOLDER=b1gm5lt4p9630hifld2j
curl -sS https://ai.api.cloud.yandex.net/v1/chat/completions \
  -H "Authorization: Api-Key $KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"gpt://$FOLDER/deepseek-v4-flash/latest\",\"max_tokens\":2000,
       \"temperature\":0,\"response_format\":{\"type\":\"json_object\"},
       \"messages\":[{\"role\":\"user\",\"content\":\"Верни JSON {\\\"ok\\\":true}\"}]}"
```
