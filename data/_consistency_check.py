"""Проверка внутренней консистентности витрины Meridian.
Запуск: .venv/bin/python data/_consistency_check.py
Ничего не меняет — только читает CSV и печатает расхождения.
"""
import pandas as pd
import numpy as np
from pathlib import Path

D = Path(__file__).parent / "meridian_dwh"
def load(name): return pd.read_csv(D / f"{name}.csv")

print("Загрузка...")
customers = load("customers")
orders = load("orders")
activity = load("customer_activity_monthly")
fin = load("financials_monthly")
ue = load("unit_economics_monthly")
nps = load("nps_responses")
pl = load("product_lines")
churn = load("churn_reasons")

for df, n in [(customers,'customers'),(orders,'orders'),(activity,'activity'),
              (fin,'financials'),(ue,'unit_economics'),(nps,'nps'),(pl,'product_lines'),(churn,'churn_reasons')]:
    print(f"  {n:14s} {len(df):>8} строк, {df.shape[1]} колонок")

# даты
for df, cols in [(customers,['signup_date','churn_date']),(orders,['order_date']),
                 (activity,['month']),(fin,['month']),(ue,['month']),(nps,['response_date']),
                 (pl,['launch_date']),(churn,['churn_date'])]:
    for c in cols:
        df[c] = pd.to_datetime(df[c], errors='coerce')

issues = []
def check(name, cond_ok, detail=""):
    status = "OK " if cond_ok else "!!!"
    print(f"[{status}] {name}  {detail}")
    if not cond_ok: issues.append(name)

print("\n=== 1. Уникальность ключей ===")
check("customers.customer_id unique", customers.customer_id.is_unique)
check("orders.order_id unique", orders.order_id.is_unique)
check("nps.response_id unique", nps.response_id.is_unique)
check("product_lines.product_line_id unique", pl.product_line_id.is_unique)
check("activity (customer_id,month) unique", not activity.duplicated(['customer_id','month']).any())
check("financials.month unique", fin.month.is_unique)
check("ue (month,segment,product_line_id) unique", not ue.duplicated(['month','segment','product_line_id']).any())
check("churn.customer_id unique (1:1)", churn.customer_id.is_unique)

print("\n=== 2. Целостность FK ===")
cset = set(customers.customer_id)
plset = set(pl.product_line_id)
check("orders.customer_id ⊆ customers", set(orders.customer_id) <= cset,
      f"missing={len(set(orders.customer_id)-cset)}")
check("orders.product_line_id ⊆ product_lines", set(orders.product_line_id) <= plset,
      f"missing={len(set(orders.product_line_id)-plset)}")
check("activity.customer_id ⊆ customers", set(activity.customer_id) <= cset,
      f"missing={len(set(activity.customer_id)-cset)}")
check("nps.customer_id ⊆ customers", set(nps.customer_id) <= cset,
      f"missing={len(set(nps.customer_id)-cset)}")
check("nps.product_line_id ⊆ product_lines", set(nps.product_line_id) <= plset,
      f"missing={len(set(nps.product_line_id)-plset)}")
check("churn.customer_id ⊆ customers", set(churn.customer_id) <= cset,
      f"missing={len(set(churn.customer_id)-cset)}")
check("ue.product_line_id ⊆ product_lines", set(ue.product_line_id) <= plset)

print("\n=== 3. churn_reasons vs customers.churn_date ===")
# все в churn_reasons должны иметь churn_date в customers
churned_customers = customers[customers.churn_date.notna()]
check("все churn_reasons.customer_id имеют churn_date в customers",
      set(churn.customer_id) <= set(churned_customers.customer_id),
      f"без churn_date={len(set(churn.customer_id)-set(churned_customers.customer_id))}")
m = churn.merge(customers[['customer_id','churn_date']], on='customer_id', suffixes=('_cr','_cust'))
mism = (m.churn_date_cr != m.churn_date_cust).sum()
check("churn_date совпадает в churn_reasons и customers", mism==0, f"расхождений={mism}")
print(f"     churned клиентов: {len(churned_customers)}, строк в churn_reasons: {len(churn)}, "
      f"покрытие exit-интервью: {churn.interview_completed.mean()*100:.1f}%")

print("\n=== 4. nps: category vs score ===")
def cat(s):
    return 'promoter' if s>=9 else ('passive' if s>=7 else 'detractor')
bad = (nps.category != nps.score.map(cat)).sum()
check("nps.category соответствует score", bad==0, f"расхождений={bad}")
check("nps.score в [0,10]", nps.score.between(0,10).all())

print("\n=== 5. orders: суммы и статусы ===")
check("orders.status ∈ {completed,cancelled,refunded,disputed}",
      set(orders.status) <= {'completed','cancelled','refunded','disputed'},
      f"{set(orders.status)}")
check("orders.gmv >= 0", (orders.gmv>=0).all())
check("orders.revenue >= 0", (orders.revenue>=0).all())
# take rate на заказ
orders['tr'] = orders.revenue / orders.gmv.replace(0, np.nan)
print(f"     order take_rate: min={orders.tr.min():.4f} max={orders.tr.max():.4f} mean={orders.tr.mean():.4f}")

print("\n=== 6. financials: формулы ===")
tr_calc = fin.revenue_gross / fin.gmv
check("take_rate == revenue_gross/gmv", np.allclose(fin.take_rate, tr_calc, atol=1e-4),
      f"max_diff={np.abs(fin.take_rate-tr_calc).max():.6f}")
ebitda_calc = fin.revenue_net - fin.cogs - fin.opex_marketing - fin.opex_rnd - fin.opex_admin
check("ebitda == revenue_net - cogs - opex", np.allclose(fin.ebitda, ebitda_calc, atol=1.0),
      f"max_diff={np.abs(fin.ebitda-ebitda_calc).max():.1f}")
check("revenue_net <= revenue_gross", (fin.revenue_net<=fin.revenue_gross).all())
check("financials 36 месяцев", len(fin)==36, f"={len(fin)}")

print("\n=== 7. financials.gmv vs sum(orders.gmv) по месяцам ===")
o = orders.copy()
o['month'] = o.order_date.values.astype('datetime64[M]').astype('datetime64[ns]')
# Учитываем ли только completed? Проверим оба варианта
om_all = o.groupby('month').gmv.sum()
om_comp = o[o.status=='completed'].groupby('month').gmv.sum()
fin_idx = fin.set_index('month').gmv
j = pd.DataFrame({'fin':fin_idx,'orders_all':om_all,'orders_completed':om_comp}).dropna()
j['ratio_all'] = j.orders_all/j.fin
j['ratio_comp'] = j.orders_completed/j.fin
print(f"     ratio orders_all/fin:        mean={j.ratio_all.mean():.3f} (min {j.ratio_all.min():.3f}, max {j.ratio_all.max():.3f})")
print(f"     ratio orders_completed/fin:  mean={j.ratio_comp.mean():.3f} (min {j.ratio_comp.min():.3f}, max {j.ratio_comp.max():.3f})")

print("\n=== 8. activity vs orders (orders_count, gmv_total) ===")
o2 = o[o.status=='completed'] if False else o  # сравним с completed и all ниже
agg_all = o.groupby(['customer_id','month']).agg(oc=('order_id','count'), gmv=('gmv','sum')).reset_index()
am = activity.merge(agg_all, on=['customer_id','month'], how='left').fillna({'oc':0,'gmv':0})
oc_match = (am.orders_count == am.oc).mean()*100
gmv_match = np.isclose(am.gmv_total, am.gmv, atol=1.0).mean()*100
print(f"     orders_count == activity (all orders):  совпадение {oc_match:.1f}%")
print(f"     gmv_total == activity (all orders):      совпадение {gmv_match:.1f}%")
# и для completed
aggc = o[o.status=='completed'].groupby(['customer_id','month']).agg(oc=('order_id','count'), gmv=('gmv','sum')).reset_index()
amc = activity.merge(aggc, on=['customer_id','month'], how='left').fillna({'oc':0,'gmv':0})
print(f"     orders_count == activity (completed):    совпадение {(amc.orders_count==amc.oc).mean()*100:.1f}%")
print(f"     gmv_total == activity (completed):       совпадение {np.isclose(amc.gmv_total,amc.gmv,atol=1.0).mean()*100:.1f}%")

print("\n=== 9. activity.status vs churn_date ===")
act = activity.merge(customers[['customer_id','churn_date']], on='customer_id', how='left')
# churned должно быть когда churn_date<=month
churned_rows = act[act.status=='churned']
bad_churned = (churned_rows.churn_date.isna() | (churned_rows.churn_date > churned_rows.month)).sum()
check("status=churned => churn_date<=month", bad_churned==0, f"нарушений={bad_churned}")
active_dormant = act[act.status.isin(['active','dormant','churning'])]
bad_active = (active_dormant.churn_date.notna() & (active_dormant.churn_date <= active_dormant.month)).sum()
check("status∈{active,dormant,churning} => churn_date IS NULL или >month", bad_active==0,
      f"нарушений={bad_active}")
# active => был заказ в месяце
act_status = act[act.status=='active'].merge(agg_all, on=['customer_id','month'], how='left')
no_order_active = (act_status.oc.fillna(0)==0).sum()
check("status=active => есть заказ в месяце", no_order_active==0, f"active без заказа={no_order_active}")

print("\n=== 10. диапазоны дат ===")
print(f"     orders: {orders.order_date.min().date()} .. {orders.order_date.max().date()}")
print(f"     activity: {activity.month.min().date()} .. {activity.month.max().date()}")
print(f"     financials: {fin.month.min().date()} .. {fin.month.max().date()}")
print(f"     signup: {customers.signup_date.min().date()} .. {customers.signup_date.max().date()}")
print(f"     churn_date: {customers.churn_date.min().date()} .. {customers.churn_date.max().date()}")
# заказы до регистрации?
om = orders.merge(customers[['customer_id','signup_date','churn_date']], on='customer_id')
before_signup = (om.order_date < om.signup_date).sum()
check("нет заказов до signup_date", before_signup==0, f"нарушений={before_signup}")
after_churn = (om.churn_date.notna() & (om.order_date > om.churn_date)).sum()
print(f"     заказов после churn_date: {after_churn} ({after_churn/len(om)*100:.2f}%)")

print("\n=== 11. сегменты / категории ===")
check("customers.segment ∈ {SMB,Mid,Large}", set(customers.segment)<={'SMB','Mid','Large'}, f"{set(customers.segment)}")
check("ue.segment ∈ {SMB,Mid,Large}", set(ue.segment)<={'SMB','Mid','Large'}, f"{set(ue.segment)}")
check("pl.category ∈ {high,mid,low}_margin", set(pl.category)<={'high_margin','mid_margin','low_margin'})

print("\n" + "="*50)
if issues:
    print(f"НАЙДЕНО РАСХОЖДЕНИЙ: {len(issues)}")
    for i in issues: print("  - "+i)
else:
    print("Жёстких нарушений целостности не найдено (см. мягкие метрики выше).")
