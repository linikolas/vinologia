# app.py
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime, date

# -------------------- Константы конфигурации --------------------
PAGE_TITLE = "Побокальные вина — отчёт (только таблицы, по неделям)"
LAYOUT = "wide"

# Фильтр по категории (жёстко задан, не редактируется пользователем)
ARTICLE_CATEGORY_FILTER = "вина_по_бокалам_150_мл"

# Пороги ABC / XYZ (фиксированы; выводим как справку)
ABC_A = 0.80
ABC_B = 0.95
XYZ_X = 0.35
XYZ_Y = 0.80

# Необязательный «тихий» путь: если файл не загружают через UI — попробуем прочитать отсюда
# (путь не отображается пользователю)
FILE_PATH = Path("/Users/nl/streamlit_test/report_dish_new_menu.xlsx")

# Ожидаемые названия столбцов (данные уже предобработаны)
COL_DATETIME = "open_time"
COL_NAME = "article_name"
COL_CATEGORY = "article_category"
COL_GLASS_CAT = "only_glass_cat"
COL_GLASS_PRICE = "glass_price"
COL_GLASS_PROFIT = "glass_profit"
COL_QTY = "quantity"

# -------------------- Оформление страницы --------------------
st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT)
st.title(PAGE_TITLE)

# -------------------- Загрузка данных --------------------
uploaded_file = st.file_uploader("Загрузите Excel (xlsx/xls)", type=["xlsx", "xls"])

def load_dataframe():
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    # тихая попытка прочитать из FILE_PATH
    if FILE_PATH.exists() and FILE_PATH.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(FILE_PATH)
    st.error("Файл не загружен. Загрузите Excel-файл.")
    st.stop()

df_raw = load_dataframe()

# -------------------- Единственный контрол: дата-граница --------------------
filter_after = st.date_input("Показывать продажи ПОСЛЕ даты", value=date(2025, 6, 23))

# -------------------- Информативный блок: что за фильтры и пороги используются --------------------
st.info(
    f"""
**Фиксированные настройки отчёта**  
- Фильтр `article_category`: **{ARTICLE_CATEGORY_FILTER}**  
- ABC: A до {int(ABC_A*100)}%, B до {int(ABC_B*100)}% кумулятивной выручки  
- XYZ (по недельному CV): X ≤ {XYZ_X}, Y ≤ {XYZ_Y}, иначе Z  
- Выручка/прибыль считаются как Σ(цена/прибыль за бокал × количество):
  `total_revenue = Σ(glass_price × quantity)`, `profit = Σ(glass_profit × quantity)`
"""
)

# -------------------- Проверка обязательных колонок --------------------
required_cols = [
    COL_DATETIME, COL_NAME, COL_CATEGORY, COL_GLASS_CAT,
    COL_GLASS_PRICE, COL_GLASS_PROFIT, COL_QTY
]
missing = [c for c in required_cols if c not in df_raw.columns]
if missing:
    st.error(f"В файле отсутствуют обязательные колонки: {missing}")
    st.dataframe(df_raw.head(20), use_container_width=True)
    st.stop()

# -------------------- Подготовка данных --------------------
df = df_raw.copy()

# Дата/время и период неделя
df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME], errors="coerce")
df = df.dropna(subset=[COL_DATETIME]).copy()
df["week"] = df[COL_DATETIME].dt.to_period("W")     # недели (по умолчанию до воскресенья)
df["date"] = df[COL_DATETIME].dt.date

# Идентификаторы / категории
df["name"] = df[COL_NAME].astype(str)
df["article_category"] = df[COL_CATEGORY].astype(str)
df["only_glass_cat"] = df[COL_GLASS_CAT].astype(str)

# Количество
df["qty"] = pd.to_numeric(df[COL_QTY], errors="coerce").fillna(0.0)

# Выручка и прибыль: цена/прибыль за бокал × количество
price_per_glass = pd.to_numeric(df[COL_GLASS_PRICE], errors="coerce").fillna(0.0)
profit_per_glass = pd.to_numeric(df[COL_GLASS_PROFIT], errors="coerce").fillna(0.0)
df["total_revenue"] = price_per_glass * df["qty"]
df["profit"] = profit_per_glass * df["qty"]

# Фильтр по дате
cutoff_dt = datetime.combine(filter_after, datetime.min.time())
df = df.loc[df[COL_DATETIME] > cutoff_dt].copy()
if df.empty:
    st.warning("После выбранной даты данных нет.")
    st.stop()

# Фильтр по категории (жёстко задан)
df = df.loc[df["article_category"] == ARTICLE_CATEGORY_FILTER].copy()
if df.empty:
    st.warning(f"В категории '{ARTICLE_CATEGORY_FILTER}' данных нет.")
    st.stop()

st.caption(f"Фильтр: article_category == '{ARTICLE_CATEGORY_FILTER}'. Строк после фильтра: {len(df):,}".replace(",", " "))

# -------------------- Агрегации по неделям и позициям --------------------
weekly = df.groupby(["name", "week"], as_index=False)[["total_revenue", "profit"]].sum()

# Базовые метрики по позиции (на основе недельных сумм)
stats = weekly.groupby("name").agg(
    total_revenue=("total_revenue", "sum"),
    profit=("profit", "sum"),
    mean_rev=("total_revenue", "mean"),
    std_rev=("total_revenue", "std"),
    weeks_sold=("week", "count"),
).reset_index()

# Недельный CV и coverage
stats["cv"] = stats["std_rev"] / stats["mean_rev"]
stats.loc[~np.isfinite(stats["cv"]), "cv"] = np.nan
total_weeks = weekly["week"].nunique()
stats["coverage"] = stats["weeks_sold"] / (total_weeks if total_weeks else 1)

# Последняя неделя продажи
last_sold = weekly.groupby("name")["week"].max().reset_index().rename(columns={"week": "last_sold"})
stats = stats.merge(last_sold, on="name", how="left")

# Маржа, %
stats["margin_pct"] = np.where(
    stats["total_revenue"] > 0,
    stats["profit"] / stats["total_revenue"] * 100,
    np.nan
)

# Основная подкатегория only_glass_cat (по максимальной выручке позиции в ней)
glass_map = (
    df.groupby(["name", "only_glass_cat"], as_index=False)["total_revenue"].sum()
      .sort_values(["name", "total_revenue"], ascending=[True, False])
      .drop_duplicates("name")[["name", "only_glass_cat"]]
      .rename(columns={"only_glass_cat": "main_glass_cat"})
)
stats = stats.merge(glass_map, on="name", how="left")

# -------------------- ABC (по total_revenue, в текущем фильтре) --------------------
by_item = (
    df.groupby("name", as_index=False)
      .agg(revenue=("total_revenue", "sum"))
      .sort_values("revenue", ascending=False)
      .reset_index(drop=True)
)
sum_revenue = by_item["revenue"].sum()
by_item["rev_share"] = np.where(sum_revenue > 0, by_item["revenue"] / sum_revenue, 0.0)
by_item["cum_share"] = by_item["rev_share"].cumsum()

def abc_bucket(cum_share: float, a: float = ABC_A, b: float = ABC_B) -> str:
    if cum_share <= a:
        return "A"
    if cum_share <= b:
        return "B"
    return "C"

by_item["ABC"] = by_item["cum_share"].apply(abc_bucket)

# -------------------- XYZ (метка по недельному CV) --------------------
# Рассчитываем ещё раз mean/std по недельным суммам (эквивалентно stats, но оставим отдельно для чистоты)
xyz_basis = weekly.groupby("name")["total_revenue"].agg(mean="mean", std="std").reset_index()
xyz_basis["cv_xyz"] = xyz_basis["std"] / xyz_basis["mean"]

def xyz_bucket(cv_value: float, x_thr: float = XYZ_X, y_thr: float = XYZ_Y) -> str:
    if pd.isna(cv_value) or cv_value == np.inf:
        return "Z"
    if cv_value <= x_thr:
        return "X"
    if cv_value <= y_thr:
        return "Y"
    return "Z"

xyz_basis["XYZ"] = xyz_basis["cv_xyz"].apply(xyz_bucket)

# -------------------- Сборка итогового отчёта --------------------
report = (
    stats.merge(by_item[["name", "rev_share", "cum_share", "ABC"]], on="name", how="left")
         .merge(xyz_basis[["name", "XYZ"]], on="name", how="left")  # численный cv берём из stats["cv"]
)

# Сортировка: ABC (A→B→C), затем XYZ (X→Y→Z), затем по выручке
order_abc = {"A": 0, "B": 1, "C": 2}
order_xyz = {"X": 0, "Y": 1, "Z": 2}
report["abc_ord"] = report["ABC"].map(order_abc).fillna(9)
report["xyz_ord"] = report["XYZ"].map(order_xyz).fillna(9)
report = report.sort_values(["abc_ord", "xyz_ord", "total_revenue"], ascending=[True, True, False]).reset_index(drop=True)

# -------------------- Вывод таблиц: одна таблица на каждую only_glass_cat --------------------
st.subheader("Только таблицы: 1 подкатегория (only_glass_cat) = 1 таблица")

columns_to_show = [
    "name", "total_revenue", "profit", "margin_pct",
    "weeks_sold", "coverage", "last_sold",
    "cv", "ABC", "XYZ", "rev_share", "cum_share"
]

glass_categories = (
    df.groupby("only_glass_cat", as_index=False)["total_revenue"].sum()
      .sort_values("total_revenue", ascending=False)["only_glass_cat"]
      .tolist()
)

if not glass_categories:
    st.write("Подкатегорий (only_glass_cat) не найдено.")
else:
    st.caption(f"Подкатегорий (only_glass_cat): {len(glass_categories)}")
    for gcat in glass_categories:
        items_in_gcat = df.loc[df["only_glass_cat"] == gcat, "name"].unique().tolist()
        table = report.loc[report["name"].isin(items_in_gcat), columns_to_show].reset_index(drop=True)
        st.markdown(f"### {gcat}")
        st.dataframe(table, use_container_width=True, hide_index=True)
