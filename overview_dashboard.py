"""Обзорный дашборд витрины Meridian — что за данные и о чём они говорят.
Генерирует overview_dashboard.png из реальных CSV в data/meridian_dwh/."""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager

# поддержка кириллицы
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

D = "data/meridian_dwh"
fin = pd.read_csv(f"{D}/financials_monthly.csv", parse_dates=["month"])
cust = pd.read_csv(f"{D}/customers.csv", parse_dates=["signup_date", "churn_date"])
act = pd.read_csv(f"{D}/customer_activity_monthly.csv", parse_dates=["month"])
pl = pd.read_csv(f"{D}/product_lines.csv")
orders = pd.read_csv(f"{D}/orders.csv", parse_dates=["order_date"])
churn = pd.read_csv(f"{D}/churn_reasons.csv")

fig, axes = plt.subplots(2, 3, figsize=(20, 11))
fig.suptitle("Витрина Meridian — обзор данных (2023–2025)", fontsize=20, fontweight="bold")

# 1. GMV растёт, но gross revenue падает
ax = axes[0, 0]
ax.plot(fin.month, fin.gmv / 1e9, color="#2e86de", lw=2.5, label="GMV (оборот), млрд ₽")
ax2 = ax.twinx()
ax2.plot(fin.month, fin.revenue_gross / 1e9, color="#e74c3c", lw=2.5, label="Gross revenue, млрд ₽")
ax.set_title("1. GMV vs выручка: оборот растёт, комиссия падает", fontweight="bold")
ax.set_ylabel("GMV, млрд ₽", color="#2e86de")
ax2.set_ylabel("Gross revenue, млрд ₽", color="#e74c3c")
lines = ax.get_lines() + ax2.get_lines()
ax.legend(lines, [l.get_label() for l in lines], loc="upper left", fontsize=8)

# 2. EBITDA уходит в минус
ax = axes[0, 1]
colors = ["#27ae60" if v >= 0 else "#c0392b" for v in fin.ebitda]
ax.bar(fin.month, fin.ebitda / 1e9, width=20, color=colors)
ax.axhline(0, color="black", lw=0.8)
ax.set_title("2. EBITDA: из плюса в минус", fontweight="bold")
ax.set_ylabel("EBITDA, млрд ₽")

# 3. Скрытый отток: структура статусов активности по месяцам
ax = axes[0, 2]
counts = act.groupby(["month", "status"]).size().unstack(fill_value=0)
status_share = counts.div(counts.sum(axis=1), axis=0)
order = ["active", "dormant", "churning", "churned"]
cmap = {"active": "#27ae60", "dormant": "#f39c12", "churning": "#e67e22", "churned": "#7f8c8d"}
bottom = 0
for st in order:
    if st in status_share:
        ax.fill_between(status_share.index, bottom, bottom + status_share[st] * 100,
                        label=st, color=cmap[st], alpha=0.9)
        bottom = bottom + status_share[st] * 100
ax.set_title("3. Скрытый отток: статусы активности клиентов", fontweight="bold")
ax.set_ylabel("% клиентских месяцев")
ax.legend(loc="lower left", fontsize=8)
ax.set_ylim(0, 100)

# 4. Сегменты клиентов
ax = axes[1, 0]
seg = cust.segment.value_counts()
ax.pie(seg.values, labels=seg.index, autopct="%1.0f%%", startangle=90,
       colors=["#3498db", "#9b59b6", "#1abc9c"])
ax.set_title(f"4. Клиенты по сегментам (всего {len(cust):,})".replace(",", " "), fontweight="bold")

# 5. Выручка по продуктовым линиям (по категории маржинальности)
ax = axes[1, 1]
om = orders.merge(pl[["product_line_id", "name", "category"]], on="product_line_id")
rev_by_line = om.groupby("name").revenue.sum().sort_values() / 1e6
catcol = {"high_margin": "#27ae60", "mid_margin": "#f39c12", "low_margin": "#c0392b"}
namecat = pl.set_index("name").category.to_dict()
bar_colors = [catcol.get(namecat.get(n), "#888") for n in rev_by_line.index]
ax.barh(rev_by_line.index, rev_by_line.values, color=bar_colors)
ax.set_title("5. Выручка по продуктовым линиям, млн ₽", fontweight="bold")
ax.tick_params(axis="y", labelsize=8)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in catcol.values()]
ax.legend(handles, catcol.keys(), fontsize=8, loc="lower right")

# 6. Причины оттока
ax = axes[1, 2]
reasons = churn.primary_reason.value_counts()
ax.bar(reasons.index, reasons.values, color="#8e44ad")
ax.set_title(f"6. Причины оттока (exit-интервью, n={len(churn):,})".replace(",", " "), fontweight="bold")
ax.set_ylabel("кол-во клиентов")
ax.tick_params(axis="x", rotation=30, labelsize=8)

for row in axes:
    for ax in row:
        ax.tick_params(axis="x", labelsize=8)

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig("overview_dashboard.png", dpi=120, bbox_inches="tight")
print("Сохранено: overview_dashboard.png")

# текстовая сводка
print("\n=== РАЗМЕРЫ ТАБЛИЦ ===")
for name, df in [("financials_monthly", fin), ("customers", cust), ("orders", orders),
                 ("customer_activity_monthly", act), ("churn_reasons", churn), ("product_lines", pl)]:
    print(f"{name:30s} {len(df):>8,} строк  ×  {df.shape[1]} полей".replace(",", " "))
print(f"\nПериод financials: {fin.month.min().date()} → {fin.month.max().date()}")
print(f"Активных клиентов (churn_date пуст): {cust.churn_date.isna().sum():,}".replace(",", " "))
print(f"Ушедших клиентов: {cust.churn_date.notna().sum():,}".replace(",", " "))
