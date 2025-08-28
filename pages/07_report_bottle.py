# app.py
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime, date

st.set_page_config(page_title="Ликвидность ассортимента — таблицы", layout="wide")
st.title("Ликвидность ассортимента (минималистично) — только таблицы")

# --------- Ввод: файл и фильтр даты (без сайдбара) ----------
col_a, col_b = st.columns([2, 1])
with col_a:
    uploaded = st.file_uploader("Загрузите Excel (report_dish_new_menu.xlsx или all_sales.xlsx)", type=["xlsx", "xls"])
with col_b:
    local_path = st.text_input("...или путь к файлу на диске", value="/Users/nl/streamlit_test/report_dish_new_menu.xlsx")

col1, col2, col3 = st.columns([1,1,1])
with col1:
    filter_after = st.date_input("Показывать после даты", value=date(2025, 6, 23))
with col2:
    abc_a = st.slider("ABC: граница A (доля)", 0.5, 0.9, 0.80, 0.01)
with col3:
    xyz_x = st.slider("XYZ: X (CV ≤)", 0.1, 1.0, 0.35, 0.05)
xyz_y = st.slider("XYZ: Y (CV ≤)", 0.2, 2.0, 0.80, 0.05)

st.markdown("---")

# --------- Загрузка ----------
LIKELY_COLUMNS = {
    "datetime": ["open_time","date","datetime","sold_at","time"],
    "name":     ["article_name","name","item","sku","position","wine_name"],
    "revenue":  ["final_sum","sum","revenue","amount","line_sum"],
    "qty":      ["quantity","qty","count","pcs"],
    "profit_a": ["article_profit","profit","profit_sum"],
    "profit_g": ["glass_profit"],
    "category": ["article_category","category","cat"],
}

def pick(df, options):
    for c in options:
        if c in df.columns: return c
    return None

def load_df():
    if uploaded is not None:
        return pd.read_excel(uploaded)
    p = local_path.strip()
    if p:
        pth = Path(p)
        if pth.exists():
            return pd.read_excel(pth) if pth.suffix.lower() in [".xlsx",".xls"] else None
    # попробовать локальный файл для удобства
    demo = Path("report_dish_new_menu.xlsx")
    if demo.exists():
        st.info("Использую локальный report_dish_new_menu.xlsx")
        return pd.read_excel(demo)
    return None

df_raw = load_df()
if df_raw is None:
    st.stop()

# --------- Маппинг столбцов ----------
dt_col = pick(df_raw, LIKELY_COLUMNS["datetime"])
nm_col = pick(df_raw, LIKELY_COLUMNS["name"])
rv_col = pick(df_raw, LIKELY_COLUMNS["revenue"])
qt_col = pick(df_raw, LIKELY_COLUMNS["qty"])
pa_col = pick(df_raw, LIKELY_COLUMNS["profit_a"])
pg_col = pick(df_raw, LIKELY_COLUMNS["profit_g"])
ct_col = pick(df_raw, LIKELY_COLUMNS["category"])

need = {"datetime": dt_col, "name": nm_col, "revenue": rv_col, "category": ct_col}
missing = [k for k,v in need.items() if v is None]
if missing:
    st.error(f"Не нашёл колонки: {missing}. Переименуйте столбцы или добавьте их варианты в код.")
    st.dataframe(df_raw.head(20), use_container_width=True)
    st.stop()

# --------- Подготовка ----------
df = df_raw.copy()
df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
df = df.dropna(subset=[dt_col]).copy()
df["month"] = df[dt_col].dt.to_period("M")
df["date"]  = df[dt_col].dt.date

df["name"] = df[nm_col].astype(str)
df["category"] = df[ct_col].astype(str)

df["revenue"] = pd.to_numeric(df[rv_col], errors="coerce").fillna(0.0)
df["qty"] = pd.to_numeric(df[qt_col], errors="coerce").fillna(1.0) if qt_col else 1.0

profits = []
if pa_col: profits.append(pd.to_numeric(df[pa_col], errors="coerce"))
if pg_col: profits.append(pd.to_numeric(df[pg_col], errors="coerce"))
df["profit"] = pd.concat(profits, axis=1).max(axis=1) if profits else np.nan

# Фильтр по дате
cutoff = datetime.combine(filter_after, datetime.min.time())
df = df.loc[df[dt_col] > cutoff].copy()
if df.empty:
    st.warning("После выбранной даты данных нет.")
    st.stop()

# --------- Агрегации по месяцам и позициям ----------
monthly = df.groupby(["name","month"], as_index=False)["revenue"].sum()

# Базовые метрики по позиции
stats = monthly.groupby("name")["revenue"].agg(
    total_revenue="sum",
    mean_rev="mean",
    std_rev="std",
    months_sold="count",
).reset_index()

# CV и coverage
stats["cv"] = stats["std_rev"] / stats["mean_rev"]
total_months = monthly["month"].nunique()
stats["coverage"] = stats["months_sold"] / (total_months if total_months else 1)

# Последний месяц продажи
last_sold = monthly.groupby("name")["month"].max().reset_index().rename(columns={"month":"last_sold"})
stats = stats.merge(last_sold, on="name", how="left")

# Прибыль и маржа
profit_item = df.groupby("name", as_index=False)["profit"].sum()
stats = stats.merge(profit_item, on="name", how="left")
stats["profit"] = stats["profit"].fillna(0.0)
stats["margin_pct"] = np.where(stats["total_revenue"]>0, stats["profit"]/stats["total_revenue"]*100, np.nan)

# Привязка основной категории (берём ту, где у позиции наибольшая выручка)
cat_map = (
    df.groupby(["name","category"], as_index=False)["revenue"].sum()
      .sort_values(["name","revenue"], ascending=[True, False])
      .drop_duplicates("name")[["name","category"]]
      .rename(columns={"category":"main_category"})
)
stats = stats.merge(cat_map, on="name", how="left")

# --------- ABC ----------
by_item = df.groupby("name", as_index=False).agg(revenue=("revenue","sum"))
by_item = by_item.sort_values("revenue", ascending=False).reset_index(drop=True)
total_rev = by_item["revenue"].sum()
by_item["rev_share"] = np.where(total_rev>0, by_item["revenue"]/total_rev, 0.0)
by_item["cum_share"] = by_item["rev_share"].cumsum()

def abc_bucket(x, a=0.80, b=0.95):
    if x <= a: return "A"
    if x <= b: return "B"
    return "C"

by_item["ABC"] = by_item["cum_share"].apply(lambda x: abc_bucket(x, abc_a, 0.95))

# --------- XYZ ----------
daily = df.groupby(["name", df["month"].dt.to_timestamp("D")], as_index=False)["revenue"].sum()
xyz = daily.groupby("name")["revenue"].agg(mean="mean", std="std").reset_index()
xyz["cv"] = xyz["std"] / xyz["mean"]

def xyz_bucket(cv, x_thr, y_thr):
    if pd.isna(cv) or cv == np.inf: return "Z"
    if cv <= x_thr: return "X"
    if cv <= y_thr: return "Y"
    return "Z"

xyz["XYZ"] = xyz["cv"].apply(lambda v: xyz_bucket(v, xyz_x, xyz_y))

# --------- Сборка отчёта ----------
report = (
    stats.merge(by_item[["name","rev_share","cum_share","ABC"]], on="name", how="left")
         .merge(xyz[["name","XYZ"]], on="name", how="left")
)

# Сортировка для удобства просмотра
order_abc = {"A":0,"B":1,"C":2}
order_xyz = {"X":0,"Y":1,"Z":2}
report["abc_ord"] = report["ABC"].map(order_abc).fillna(9)
report["xyz_ord"] = report["XYZ"].map(order_xyz).fillna(9)
report = report.sort_values(["abc_ord","xyz_ord","total_revenue"], ascending=[True,True,False])

# --------- Вывод: одна таблица на КАЖДУЮ категорию ----------
st.subheader("Только таблицы (1 категория = 1 таблица)")
show_cols = [
    "name","total_revenue","profit","margin_pct","months_sold","coverage","last_sold",
    "cv","ABC","XYZ","rev_share","cum_share"
]

categories = (
    df.groupby("category", as_index=False)["revenue"].sum()
      .sort_values("revenue", ascending=False)["category"]
      .tolist()
)

if not categories:
    st.write("Категорий нет.")
else:
    st.caption(f"Категорий: {len(categories)}")
    for cat in categories:
        names_in_cat = df.loc[df["category"]==cat, "name"].unique().tolist()
        table = report.loc[report["name"].isin(names_in_cat), show_cols].reset_index(drop=True)
        st.markdown(f"### {cat}")
        st.dataframe(table, use_container_width=True, hide_index=True)
