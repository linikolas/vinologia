# app.py
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime, date

st.set_page_config(page_title="Побокальные вина — отчёт (только таблицы, по неделям)", layout="wide")
st.title("Побокальные вина — отчёт по ликвидности (по неделям, только таблицы)")

# -------------------- Ввод: файл и параметры (без сайдбара) --------------------
col_a, col_b = st.columns([2, 1])
with col_a:
    uploaded = st.file_uploader("Загрузите Excel (например, all_sales.xlsx / report_dish_new_menu.xlsx)", type=["xlsx","xls"])
with col_b:
    local_path = st.text_input("...или путь к файлу на диске", value="/Users/nl/streamlit_test/report_dish_new_menu.xlsx")

col1, col2, col3 = st.columns([1,1,1])
with col1:
    filter_after = st.date_input("Показывать ПОСЛЕ даты", value=date(2025, 6, 23))
with col2:
    abc_a = st.slider("ABC: граница A (доля)", 0.5, 0.9, 0.80, 0.01)
with col3:
    xyz_x = st.slider("XYZ: X (CV ≤)", 0.1, 1.0, 0.35, 0.05)
xyz_y = st.slider("XYZ: Y (CV ≤)", 0.2, 2.0, 0.80, 0.05)

st.markdown("---")

default_by_glass_category = "вина_по_бокалам_150_мл"
by_glass_category = st.text_input("Фильтр по article_category (по бокалам):", value=default_by_glass_category)

# -------------------- Загрузка --------------------
LIKELY_COLUMNS = {
    "datetime":   ["open_time","date","datetime","sold_at","time"],
    "name":       ["article_name","name","item","sku","position","wine_name"],
    "category":   ["article_category","category","cat"],
    "glasscat":   ["only_glass_cat","only_glass.cat","glass_cat"],
    "glass_price":["glass_price","price_glass","sum_glass","final_sum_glass"],
    "glass_profit":["glass_profit","profit_glass"],
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
            if pth.suffix.lower() in [".xlsx",".xls"]:
                return pd.read_excel(pth)
            else:
                st.error(f"Неподдерживаемое расширение: {pth.suffix}")
                return None
        else:
            st.error("Файл по указанному пути не найден.")
            return None
    demo = Path("report_dish_new_menu.xlsx")
    if demo.exists():
        st.info("Использую локальный report_dish_new_menu.xlsx")
        return pd.read_excel(demo)
    return None

df_raw = load_df()
if df_raw is None:
    st.stop()

# -------------------- Маппинг столбцов --------------------
dt_col  = pick(df_raw, LIKELY_COLUMNS["datetime"])
nm_col  = pick(df_raw, LIKELY_COLUMNS["name"])
ct_col  = pick(df_raw, LIKELY_COLUMNS["category"])
gc_col  = pick(df_raw, LIKELY_COLUMNS["glasscat"])
gp_col  = pick(df_raw, LIKELY_COLUMNS["glass_price"])
gpr_col = pick(df_raw, LIKELY_COLUMNS["glass_profit"])

need = {
    "datetime": dt_col, "name": nm_col, "article_category": ct_col,
    "only_glass_cat": gc_col, "glass_price": gp_col, "glass_profit": gpr_col
}
missing = [k for k,v in need.items() if v is None]
if missing:
    st.error(f"Не нашёл нужные колонки: {missing}. Переименуйте столбцы или добавьте их варианты в LIKELY_COLUMNS.")
    st.dataframe(df_raw.head(20), use_container_width=True)
    st.stop()

# -------------------- Подготовка --------------------
df = df_raw.copy()

# Дата/время
df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
df = df.dropna(subset=[dt_col]).copy()
df["week"] = df[dt_col].dt.to_period("W")    # недели
df["date"] = df[dt_col].dt.date

# Идентификация
df["name"] = df[nm_col].astype(str)
df["article_category"] = df[ct_col].astype(str)
df["only_glass_cat"] = df[gc_col].astype(str)

# Выручка/прибыль — именно из glass_* колонок
df["qty"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1.0)

df["total_revenue"] = pd.to_numeric(df[gp_col], errors="coerce").fillna(0.0) * df["qty"]
df["profit"] = pd.to_numeric(df[gpr_col], errors="coerce").fillna(0.0) * df["qty"]

# Фильтр по дате
cutoff = datetime.combine(filter_after, datetime.min.time())
df = df.loc[df[dt_col] > cutoff].copy()
if df.empty:
    st.warning("После выбранной даты данных нет.")
    st.stop()

# Фильтр по article_category (по бокалам)
df = df.loc[df["article_category"] == by_glass_category].copy()
if df.empty:
    st.warning(f"В категории '{by_glass_category}' данных нет. Проверь название.")
    st.stop()

st.caption(f"Фильтр: article_category == '{by_glass_category}'. Строк: {len(df):,}".replace(","," "))

# -------------------- Агрегации по неделям и позициям --------------------
weekly = df.groupby(["name","week"], as_index=False)[["total_revenue","profit"]].sum()

# Базовые метрики по позиции (по неделям)
stats = weekly.groupby("name").agg(
    total_revenue=("total_revenue","sum"),
    profit=("profit","sum"),
    mean_rev=("total_revenue","mean"),
    std_rev=("total_revenue","std"),
    weeks_sold=("week","count"),
).reset_index()

# CV и coverage (по неделям)
stats["cv"] = stats["std_rev"] / stats["mean_rev"]
stats.loc[~np.isfinite(stats["cv"]), "cv"] = np.nan
total_weeks = weekly["week"].nunique()
stats["coverage"] = stats["weeks_sold"] / (total_weeks if total_weeks else 1)

# Последняя неделя продажи
last_sold = weekly.groupby("name")["week"].max().reset_index().rename(columns={"week":"last_sold"})
stats = stats.merge(last_sold, on="name", how="left")

# Маржа, %
stats["margin_pct"] = np.where(stats["total_revenue"]>0,
                               stats["profit"]/stats["total_revenue"]*100,
                               np.nan)

# Главная подкатегория only_glass_cat по выручке
glass_map = (
    df.groupby(["name","only_glass_cat"], as_index=False)["total_revenue"].sum()
      .sort_values(["name","total_revenue"], ascending=[True, False])
      .drop_duplicates("name")[["name","only_glass_cat"]]
      .rename(columns={"only_glass_cat":"main_glass_cat"})
)
stats = stats.merge(glass_map, on="name", how="left")

# -------------------- ABC (по total_revenue, в текущем фильтре) --------------------
by_item = df.groupby("name", as_index=False).agg(revenue=("total_revenue","sum"))
by_item = by_item.sort_values("revenue", ascending=False).reset_index(drop=True)
sum_rev = by_item["revenue"].sum()
by_item["rev_share"] = np.where(sum_rev>0, by_item["revenue"]/sum_rev, 0.0) 
by_item["cum_share"] = by_item["rev_share"].cumsum()

def abc_bucket(x, a=0.80, b=0.95):
    if x <= a: return "A"
    if x <= b: return "B"
    return "C"

by_item["ABC"] = by_item["cum_share"].apply(lambda x: abc_bucket(x, abc_a, 0.95))

# -------------------- XYZ (по недельной динамике) --------------------
# Для метки XYZ используем отдельный расчёт CV (но в отчёт берём именно метку XYZ),
# чтобы не конфликтовать с stats["cv"]
daily_w = weekly.rename(columns={"week":"period"})  # просто для ясности имени
xyz = daily_w.groupby("name")["total_revenue"].agg(mean="mean", std="std").reset_index()
xyz["cv_xyz"] = xyz["std"] / xyz["mean"]

def xyz_bucket(cv, x_thr, y_thr):
    if pd.isna(cv) or cv == np.inf: return "Z"
    if cv <= x_thr: return "X"
    if cv <= y_thr: return "Y"
    return "Z"

xyz["XYZ"] = xyz["cv_xyz"].apply(lambda v: xyz_bucket(v, xyz_x, xyz_y))

# -------------------- Сборка отчёта --------------------
report = (
    stats.merge(by_item[["name","rev_share","cum_share","ABC"]], on="name", how="left")
         .merge(xyz[["name","XYZ"]], on="name", how="left")  # cv в таблице берём из stats
)

# Сортировка для удобного чтения
order_abc = {"A":0,"B":1,"C":2}
order_xyz = {"X":0,"Y":1,"Z":2}
report["abc_ord"] = report["ABC"].map(order_abc).fillna(9)
report["xyz_ord"] = report["XYZ"].map(order_xyz).fillna(9)
report = report.sort_values(["abc_ord","xyz_ord","total_revenue"], ascending=[True,True,False]).reset_index(drop=True)

# -------------------- Вывод: по одной таблице на каждую only_glass_cat --------------------
st.subheader("Только таблицы: 1 подкатегория (only_glass_cat) = 1 таблица")

show_cols = [
    "name","total_revenue","profit","margin_pct",
    "weeks_sold","coverage","last_sold",
    "cv","ABC","XYZ","rev_share","cum_share"
]

glass_cats = (
    df.groupby("only_glass_cat", as_index=False)["total_revenue"].sum()
      .sort_values("total_revenue", ascending=False)["only_glass_cat"]
      .tolist()
)

if not glass_cats:
    st.write("Подкатегорий (only_glass_cat) не найдено.")
else:
    st.caption(f"Подкатегорий (only_glass_cat): {len(glass_cats)}")
    for gcat in glass_cats:
        names_in_gcat = df.loc[df["only_glass_cat"]==gcat, "name"].unique().tolist()
        table = report.loc[report["name"].isin(names_in_gcat), show_cols].reset_index(drop=True)
        st.markdown(f"### {gcat}")
        st.dataframe(table, use_container_width=True, hide_index=True)
