# Витрина данных Meridian — легенда (схема `meridian_dwh`)

> Источник: страница «Витрина данных Meridian» дашборда хакатона (`/data`).
> Период данных: **36 месяцев, январь 2023 — декабрь 2025**. Гранулярность — преимущественно
> месяц; для `orders` и `nps_responses` — день. Все таблицы в одной схеме `meridian_dwh`.
> **Витрину менять нельзя.** Данные синтетические, но внутренне консистентные, одинаковы для всех команд.

Объём: ~25 000 клиентов, ~200 000 заказов (фактически 681 305 строк в orders.csv — см. ниже),
~80 000 NPS-ответов, ~900 000 строк в `customer_activity_monthly`.

Локальные файлы: `data/meridian_dwh/*.csv` (+ служебные `_params.npz`, `_customers.npz` — внутренние
массивы генерации, данные полностью реконструируются из CSV).

> ⚠️ Фактические объёмы CSV (по `wc -l`) местами отличаются от заявленных «высокоуровневых»:
> orders.csv — 681 305 строк, customer_activity_monthly.csv — 608 920, nps_responses.csv — 56 164,
> customers.csv — 25 000, churn_reasons.csv — 8 873. Это нормально для синтетики — ориентируйтесь на сами файлы.

---

## Высокоуровневая карта

| Таблица | Назначение |
|---|---|
| `financials_monthly` | финансовая отчётность (P&L) |
| `unit_economics_monthly` | юнит-экономика по сегментам и продуктам |
| `customers` | справочник клиентов |
| `orders` | заказы услуг (транзакционный уровень) |
| `product_lines` | справочник продуктовых линий |
| `nps_responses` | ответы на NPS-опросы |
| `customer_activity_monthly` | помесячная активность клиентов |
| `churn_reasons` | exit-интервью с ушедшими клиентами |

---

## Таблица 1. `financials_monthly`
Помесячная финансовая отчётность за 36 месяцев. Для P&L-вопросов, CAPEX-планирования, расчёта EBITDA.
Джойнов нет — агрегированная таблица.

| Поле | Тип | Описание |
|---|---|---|
| `month` | date | Первое число месяца, **ключ таблицы** |
| `gmv` | decimal | Оборот через платформу за месяц, ₽ |
| `revenue_gross` | decimal | Валовая выручка Meridian (комиссия), ₽ |
| `revenue_net` | decimal | Чистая выручка после возвратов и компенсаций, ₽ |
| `take_rate` | decimal | Эффективная комиссия = `revenue_gross / gmv` |
| `cogs` | decimal | Себестоимость (платёжные комиссии, хостинг, поддержка) |
| `opex_marketing` | decimal | Маркетинговые расходы |
| `opex_rnd` | decimal | R&D и продуктовая разработка |
| `opex_admin` | decimal | Административные расходы |
| `ebitda` | decimal | EBITDA = `revenue_net − cogs − opex` |
| `capex` | decimal | Капитальные затраты (инфраструктура, M&A, лицензии) |
| `headcount` | int | Численность сотрудников на конец месяца |

## Таблица 2. `unit_economics_monthly`
Юнит-экономика в разрезе **сегмент × продуктовая линия × месяц**. Для вопросов про CAC, LTV, payback,
маржинальность по сегментам. Джойнится только с `product_lines`.

| Поле | Тип | Описание |
|---|---|---|
| `month` | date | Месяц |
| `segment` | varchar | Сегмент клиентов: SMB / Mid / Large |
| `product_line_id` | int | FK на `product_lines` |
| `cac` | decimal | Customer Acquisition Cost в сегменте × линии за месяц |
| `ltv_12m` | decimal | LTV за 12 месяцев на новой когорте |
| `payback_months` | decimal | Срок окупаемости CAC |
| `gross_margin_pct` | decimal | Валовая маржа линии в сегменте |
| `take_rate_effective` | decimal | Фактическая take rate в сегменте × линии |
| `new_customers` | int | Количество новых клиентов в когорте |

## Таблица 3. `customers`
Справочник клиентов-компаний. Для сегментации, расчёта оттока, демографических разрезов.

| Поле | Тип | Описание |
|---|---|---|
| `customer_id` | int | PK |
| `segment` | varchar | SMB / Mid / Large (по выручке клиента) |
| `industry` | varchar | Индустрия клиента: 12 категорий |
| `city` | varchar | Город регистрации |
| `employee_count_band` | varchar | Полоса численности: <50 / 50-200 / 200-500 / 500+ |
| `signup_date` | date | Дата регистрации на платформе |
| `churn_date` | date | Дата формального расторжения договора (**NULL = активный**) |
| `contract_type` | varchar | monthly / annual / pay_as_you_go |
| `acquisition_channel` | varchar | paid / organic / referral / direct |

## Таблица 4. `orders`
Транзакционный уровень — каждый заказ услуги. Для расчёта GMV, выручки, активности, продуктовой аналитики.

| Поле | Тип | Описание |
|---|---|---|
| `order_id` | bigint | PK |
| `customer_id` | int | FK на `customers` |
| `product_line_id` | int | FK на `product_lines` |
| `order_date` | date | Дата заказа |
| `gmv` | decimal | Стоимость заказа (то, что заплатил клиент исполнителю) |
| `revenue` | decimal | Комиссия Meridian с заказа |
| `status` | varchar | completed / cancelled / refunded / disputed |
| `provider_type` | varchar | marketplace_provider / direct_contract / api_integration |

## Таблица 5. `product_lines`
Справочник продуктовых линий. Маленькая статичная таблица для джойнов.

| Поле | Тип | Описание |
|---|---|---|
| `product_line_id` | int | PK |
| `name` | varchar | Название линии |
| `category` | varchar | high_margin / mid_margin / low_margin |
| `launch_date` | date | Когда линия запущена |
| `status` | varchar | active / sunset |

**Состав линий:**
- Маркетинг и реклама — `mid_margin`
- Юридические услуги — `high_margin`
- Разработка и IT — `high_margin`
- Бухгалтерия и финучёт — `mid_margin`
- Рекрутинг — `mid_margin`
- Логистика и склад — `low_margin`
- Аутсорс операций — `low_margin`
- Дизайн и креатив — `mid_margin`
- Консалтинг — `high_margin`, **sunset с 2024**

## Таблица 6. `nps_responses`
Ответы на NPS-опросы. Опрос рассылается **раз в квартал** клиентам, у которых был хотя бы один заказ за квартал.

| Поле | Тип | Описание |
|---|---|---|
| `response_id` | bigint | PK |
| `customer_id` | int | FK на `customers` |
| `product_line_id` | int | FK на `product_lines` (по последнему использованному продукту) |
| `response_date` | date | Дата ответа |
| `score` | int | 0–10 |
| `category` | varchar | promoter (9-10) / passive (7-8) / detractor (0-6) |
| `comment_tag` | varchar | price / quality / support / ai_competitor / churn_intent / nps_growth |

## Таблица 7. `customer_activity_monthly`
Помесячный срез активности по каждому клиенту. **Самая большая таблица** (~900k строк). Для определения
реальной активности, dormant-анализа, поведенческих метрик.

| Поле | Тип | Описание |
|---|---|---|
| `customer_id` | int | FK на `customers` |
| `month` | date | Первое число месяца |
| `orders_count` | int | Количество заказов в месяце |
| `gmv_total` | decimal | Суммарный GMV клиента за месяц |
| `days_active` | int | Сколько дней было хотя бы одно действие |
| `login_count` | int | Количество входов в систему |
| `status` | varchar | active / dormant / churning / churned |

**Логика `status`:**
- `active` — был заказ в этом месяце
- `dormant` — не было заказов 30–90 дней, но `customers.churn_date IS NULL`
- `churning` — не было заказов 90+ дней, но `customers.churn_date IS NULL`
- `churned` — `customers.churn_date <= month`

> 🔑 Ключевой инсайт кейса: формальный `churn_date` занижает реальный отток. Метрика «active economic
> customer» (есть orders/gmv за период) важнее, чем `churn_date`. Статусы dormant/churning — это скрытый отток.

## Таблица 8. `churn_reasons`
Структурированные данные exit-интервью с ушедшими клиентами. **Не путать с текстовыми транскриптами** —
те идут отдельными документами вне витрины.

| Поле | Тип | Описание |
|---|---|---|
| `customer_id` | int | FK на `customers` |
| `churn_date` | date | Дата формального ухода |
| `primary_reason` | varchar | price / quality / ai_alternative / consolidation / no_need / other |
| `competitor_named` | varchar | Конкурент, к которому ушли (NULL если не назвали) |
| `interview_completed` | bool | Заполнено ли exit-интервью (не все соглашаются) |
| `nps_at_churn` | int | Последний NPS перед уходом (NULL если не было) |

> ⚠️ `interview_completed` заполнено лишь у ~61% — причины оттока неполные, это нужно фиксировать в ответах.

---

## Связи между таблицами

Все таблицы связаны через `customer_id` и `product_line_id`. Основные джойны:

- `customers` ↔ `orders` по `customer_id` (1:N) — **основная цепочка для всего**
- `customers` ↔ `customer_activity_monthly` по `customer_id` (1:N)
- `customers` ↔ `nps_responses` по `customer_id` (1:N)
- `customers` ↔ `churn_reasons` по `customer_id` (1:1, только для ушедших)
- `orders` ↔ `product_lines` по `product_line_id` (N:1)
- `financials_monthly` — без джойнов, агрегированная таблица
- `unit_economics_monthly` — агрегаты по `segment × product_line`, джойнится только с `product_lines`

## Что НЕ входит в витрину (отдельные документы)
Сопровождающие файлы для самых сложных вопросов («почему клиенты уходят», «что стейкхолдеры думают») —
текстовые транскрипты exit-интервью и мнения стейкхолдеров, на которые в SQL-витрине ответа нет.
В публичном архиве данных их нет; вероятно, выдаются отдельно/в личном кабинете.
