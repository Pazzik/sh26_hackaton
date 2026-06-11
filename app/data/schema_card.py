SCHEMA_CARD = """\
БАЗА: DuckDB, только SELECT. Период данных: 2023-01..2025-12.

СЫРЫЕ ТАБЛИЦЫ:
- financials_monthly(month, gmv, revenue_gross, revenue_net, take_rate, cogs,
  opex_marketing, opex_rnd, opex_admin, ebitda, capex, headcount) — P&L помесячно.
- unit_economics_monthly(month, segment[SMB/Mid/Large], product_line_id, cac,
  ltv_12m, payback_months, gross_margin_pct, take_rate_effective, new_customers).
- customers(customer_id, segment, industry, city, employee_count_band, signup_date,
  churn_date[NULL=активный], contract_type, acquisition_channel).
- orders(order_id, customer_id, product_line_id, order_date, gmv, revenue,
  status[completed/cancelled/refunded/disputed], provider_type).
- product_lines(product_line_id, name, category[high/mid/low_margin], launch_date, status).
- nps_responses(response_id, customer_id, product_line_id, response_date, score[0-10],
  category[promoter/passive/detractor], comment_tag).
- customer_activity_monthly(customer_id, month, orders_count, gmv_total, days_active,
  login_count, status[active/dormant/churning/churned]).
- churn_reasons(customer_id, churn_date, primary_reason, competitor_named,
  interview_completed[~61% заполнено], nps_at_churn).

КАНОНИЧЕСКИЕ ВЬЮХИ (предпочитай их для «хитрых» метрик):
- v_pnl_monthly(month, year, ..., take_rate_calc, ebitda_margin) — P&L + производные.
- v_revenue_by_line(month, product_line, category, gmv, revenue, take_rate) — только completed.
- v_active_economic_customer(customer_id, month, orders_count, gmv_total, status,
  is_active_economic, is_dormant, is_churning) — реальный экономический отток.
- v_nps_retained(quarter, retained[=клиент так и не ушёл], category, score) — survivorship
  bias: NPS retained-базы падает при росте общего.
- v_unit_econ_segment(month, segment, new_customers, avg_cac, avg_ltv_12m, ltv_cac,
  avg_payback_months, avg_gross_margin_pct).
- v_churn_funnel(month, status, customer_months) — воронка статусов.

СВЯЗИ: customers↔orders/nps_responses/customer_activity_monthly/churn_reasons по customer_id;
orders/nps_responses↔product_lines по product_line_id.

ПРАВИЛА: для GMV/выручки фильтруй status='completed'; формальный churn_date занижает
реальный отток — для оттока используй v_active_economic_customer; exit-интервью неполные.
"""
