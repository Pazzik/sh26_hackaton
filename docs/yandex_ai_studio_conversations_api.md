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
