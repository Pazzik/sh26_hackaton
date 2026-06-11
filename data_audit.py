"""Аудит качества витрины Meridian: пропуски, дубликаты, FK-целостность,
логические противоречия, выбросы. Печатает отчёт в stdout."""
import pandas as pd
import numpy as np

D = "data/meridian_dwh"
fin = pd.read_csv(f"{D}/financials_monthly.csv", parse_dates=["month"])
ue = pd.read_csv(f"{D}/unit_economics_monthly.csv", parse_dates=["month"])
cust = pd.read_csv(f"{D}/customers.csv", parse_dates=["signup_date", "churn_date"])
orders = pd.read_csv(f"{D}/orders.csv", parse_dates=["order_date"])
pl = pd.read_csv(f"{D}/product_lines.csv", parse_dates=["launch_date"])
nps = pd.read_csv(f"{D}/nps_responses.csv", parse_dates=["response_date"])
act = pd.read_csv(f"{D}/customer_activity_monthly.csv", parse_dates=["month"])
churn = pd.read_csv(f"{D}/churn_reasons.csv", parse_dates=["churn_date"])

def hdr(t): print(f"\n{'='*70}\n{t}\n{'='*70}")
def line(t): print(f"  • {t}")

# ---------- 1. ПРОПУСКИ ----------
hdr("1. ПРОПУСКИ (NULL) по таблицам")
for name, df in [("financials", fin), ("unit_econ", ue), ("customers", cust),
                 ("orders", orders), ("product_lines", pl), ("nps", nps),
                 ("activity", act), ("churn_reasons", churn)]:
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        line(f"{name}: " + ", ".join(f"{c}={n} ({n/len(df)*100:.1f}%)" for c, n in nulls.items()))
    else:
        line(f"{name}: пропусков нет")

# ---------- 2. ДУБЛИКАТЫ КЛЮЧЕЙ ----------
hdr("2. ДУБЛИКАТЫ первичных ключей")
for name, df, key in [("customers.customer_id", cust, "customer_id"),
                      ("orders.order_id", orders, "order_id"),
                      ("nps.response_id", nps, "response_id"),
                      ("product_lines.product_line_id", pl, "product_line_id"),
                      ("financials.month", fin, "month")]:
    d = df[key].duplicated().sum()
    line(f"{name}: {d} дублей")
# составные ключи
for name, df, keys in [("activity (customer×month)", act, ["customer_id", "month"]),
                       ("unit_econ (month×seg×line)", ue, ["month", "segment", "product_line_id"]),
                       ("churn_reasons.customer_id", churn, ["customer_id"])]:
    d = df.duplicated(subset=keys).sum()
    line(f"{name}: {d} дублей по {keys}")

# ---------- 3. FK-ЦЕЛОСТНОСТЬ ----------
hdr("3. ССЫЛОЧНАЯ ЦЕЛОСТНОСТЬ (orphan FK)")
cids = set(cust.customer_id)
plids = set(pl.product_line_id)
for name, df, col, ref in [("orders.customer_id→customers", orders, "customer_id", cids),
                           ("orders.product_line_id→product_lines", orders, "product_line_id", plids),
                           ("activity.customer_id→customers", act, "customer_id", cids),
                           ("nps.customer_id→customers", nps, "customer_id", cids),
                           ("nps.product_line_id→product_lines", nps, "product_line_id", plids),
                           ("churn.customer_id→customers", churn, "customer_id", cids),
                           ("unit_econ.product_line_id→product_lines", ue, "product_line_id", plids)]:
    miss = (~df[col].isin(ref)).sum()
    line(f"{name}: {miss} битых ссылок")
# обратная сторона: клиенты без единого заказа
no_orders = len(cids - set(orders.customer_id))
line(f"клиентов без единого заказа в orders: {no_orders} из {len(cids)}")

# ---------- 4. ЛОГИЧЕСКИЕ ПРОТИВОРЕЧИЯ ----------
hdr("4. ЛОГИЧЕСКИЕ ПРОТИВОРЕЧИЯ")
# churn_date < signup_date
bad = (cust.churn_date < cust.signup_date).sum()
line(f"churn_date < signup_date (ушёл раньше регистрации): {bad}")
# заказы до регистрации / после оттока
om = orders.merge(cust[["customer_id", "signup_date", "churn_date"]], on="customer_id", how="left")
before = (om.order_date < om.signup_date).sum()
after = (om.churn_date.notna() & (om.order_date > om.churn_date)).sum()
line(f"заказы РАНЬШЕ даты регистрации клиента: {before}")
line(f"заказы ПОЗЖЕ даты оттока клиента: {after}")
# churn_reasons.churn_date vs customers.churn_date
cmp = churn.merge(cust[["customer_id", "churn_date"]], on="customer_id",
                  how="left", suffixes=("_cr", "_cust"))
mismatch = (cmp.churn_date_cr != cmp.churn_date_cust).sum()
line(f"churn_reasons.churn_date ≠ customers.churn_date: {mismatch}")
# churn_reasons для НЕ ушедших клиентов
active_in_churn = cmp.churn_date_cust.isna().sum()
line(f"churn_reasons по клиентам с пустым churn_date в customers: {active_in_churn}")
# статус 'churned' в activity, но churn_date пуст; и наоборот
am = act.merge(cust[["customer_id", "churn_date"]], on="customer_id", how="left")
churned_no_date = ((am.status == "churned") & am.churn_date.isna()).sum()
line(f"activity.status='churned', но customers.churn_date пуст: {churned_no_date}")
# NPS category vs score
bad_cat = (((nps.score >= 9) & (nps.category != "promoter")) |
           ((nps.score.between(7, 8)) & (nps.category != "passive")) |
           ((nps.score <= 6) & (nps.category != "detractor"))).sum()
line(f"nps: category не соответствует score: {bad_cat}")

# ---------- 5. ВЫБРОСЫ И АНОМАЛИИ ----------
hdr("5. ВЫБРОСЫ / ПОДОЗРИТЕЛЬНЫЕ ЗНАЧЕНИЯ")
# отрицательные деньги
for name, df, cols in [("orders", orders, ["gmv", "revenue"]),
                       ("financials", fin, ["gmv", "revenue_gross", "revenue_net", "cogs"]),
                       ("unit_econ", ue, ["cac", "ltv_12m", "payback_months"])]:
    for c in cols:
        neg = (df[c] < 0).sum()
        if neg: line(f"{name}.{c}: {neg} отрицательных значений")
# revenue > gmv в заказах (комиссия больше оборота)
rev_gt_gmv = (orders.revenue > orders.gmv).sum()
line(f"orders.revenue > orders.gmv (комиссия > оборота): {rev_gt_gmv}")
# take_rate вне [0,1]
tr_bad = (~fin.take_rate.between(0, 1)).sum()
line(f"financials.take_rate вне [0,1]: {tr_bad}")
# score вне 0..10
line(f"nps.score вне [0,10]: {(~nps.score.between(0,10)).sum()}")
# числовые выбросы по IQR в orders.gmv
def iqr_out(s):
    q1, q3 = s.quantile([.25, .75]); iqr = q3 - q1
    lo, hi = q1 - 3*iqr, q3 + 3*iqr
    return ((s < lo) | (s > hi)).sum(), hi
n_out, hi = iqr_out(orders.gmv)
line(f"orders.gmv: {n_out} экстремальных выбросов (>3·IQR, порог≈{hi:,.0f} ₽); "
     f"min={orders.gmv.min():,.0f} max={orders.gmv.max():,.0f}".replace(",", " "))
# нулевой GMV у completed-заказов
zero_completed = ((orders.status == "completed") & (orders.gmv <= 0)).sum()
line(f"orders completed с gmv<=0: {zero_completed}")
# дубли заказов (полная строка)
line(f"orders полных дублей строк: {orders.duplicated().sum()}")

# ---------- 6. ДИАПАЗОНЫ ДАТ ----------
hdr("6. ДИАПАЗОНЫ ДАТ (вне 2023-01..2025-12?)")
lo, hi = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31")
for name, s in [("orders.order_date", orders.order_date),
                ("nps.response_date", nps.response_date),
                ("customers.signup_date", cust.signup_date),
                ("customers.churn_date", cust.churn_date.dropna())]:
    out = ((s < lo) | (s > hi)).sum()
    line(f"{name}: [{s.min().date()} .. {s.max().date()}], вне периода: {out}")

# ---------- 7. КАТЕГОРИИ ----------
hdr("7. КАТЕГОРИАЛЬНЫЕ ЗНАЧЕНИЯ (что встречается)")
for name, df, col in [("customers.segment", cust, "segment"),
                      ("orders.status", orders, "status"),
                      ("activity.status", act, "status"),
                      ("customers.contract_type", cust, "contract_type"),
                      ("customers.acquisition_channel", cust, "acquisition_channel"),
                      ("churn.primary_reason", churn, "primary_reason")]:
    vals = df[col].value_counts(dropna=False).to_dict()
    line(f"{name}: {vals}")

print("\nГотово.")
