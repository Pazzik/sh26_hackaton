-- P&L с производными
CREATE OR REPLACE VIEW v_pnl_monthly AS
SELECT
    month,
    CAST(strftime(month, '%Y') AS INTEGER) AS year,
    gmv, revenue_gross, revenue_net, take_rate,
    cogs, opex_marketing, opex_rnd, opex_admin, ebitda, capex, headcount,
    revenue_gross / NULLIF(gmv, 0)   AS take_rate_calc,
    ebitda / NULLIF(revenue_net, 0)  AS ebitda_margin
FROM financials_monthly;

-- выручка/GMV/маржа по продуктовым линиям
CREATE OR REPLACE VIEW v_revenue_by_line AS
SELECT
    date_trunc('month', o.order_date) AS month,
    pl.product_line_id, pl.name AS product_line, pl.category,
    SUM(o.gmv)      AS gmv,
    SUM(o.revenue)  AS revenue,
    SUM(o.revenue) / NULLIF(SUM(o.gmv), 0) AS take_rate
FROM orders o
JOIN product_lines pl USING (product_line_id)
WHERE o.status = 'completed'
GROUP BY 1, 2, 3, 4;

-- клиент-месяцы с реальной экономической активностью + флаги скрытого оттока
CREATE OR REPLACE VIEW v_active_economic_customer AS
SELECT
    cam.customer_id,
    cam.month,
    cam.orders_count,
    cam.gmv_total,
    cam.status,
    (cam.orders_count > 0 OR cam.gmv_total > 0) AS is_active_economic,
    (cam.status = 'dormant')  AS is_dormant,
    (cam.status = 'churning') AS is_churning
FROM customer_activity_monthly cam;

-- NPS отдельно по retained-базе vs ушедшим (survivorship bias).
-- retained = churn_date IS NULL (клиент так и не ушёл до конца данных): даёт цифры
-- отчёта 63.1 -> 41.6; вариант «retained на момент ответа» (churn_date > response_date)
-- даёт РАСТУЩИЙ 19 -> 35 и переворачивает нарратив (проверено по CSV 2026-06-11)
CREATE OR REPLACE VIEW v_nps_retained AS
SELECT
    date_trunc('quarter', n.response_date) AS quarter,
    (c.churn_date IS NULL) AS retained,
    n.category, n.score
FROM nps_responses n
JOIN customers c USING (customer_id);

-- юнит-экономика по сегментам: агрегация по линиям ВЗВЕШЕННАЯ по new_customers —
-- невзвешенный AVG исказил бы golden-цифры отчёта (SMB LTV/CAC 0.89, Large 3.56)
CREATE OR REPLACE VIEW v_unit_econ_segment AS
SELECT
    month, segment,
    SUM(new_customers)                                                  AS new_customers,
    SUM(cac * new_customers)      / NULLIF(SUM(new_customers), 0)       AS avg_cac,
    SUM(ltv_12m * new_customers)  / NULLIF(SUM(new_customers), 0)       AS avg_ltv_12m,
    SUM(ltv_12m * new_customers)  / NULLIF(SUM(cac * new_customers), 0) AS ltv_cac,
    SUM(payback_months * new_customers) / NULLIF(SUM(new_customers), 0) AS avg_payback_months,
    SUM(gross_margin_pct * new_customers) / NULLIF(SUM(new_customers), 0) AS avg_gross_margin_pct
FROM unit_economics_monthly
GROUP BY 1, 2;

-- воронка статусов активности по месяцам
CREATE OR REPLACE VIEW v_churn_funnel AS
SELECT
    month, status, COUNT(*) AS customer_months
FROM customer_activity_monthly
GROUP BY 1, 2;
